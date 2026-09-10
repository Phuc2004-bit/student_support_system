from __future__ import annotations

import ast
import json
from pathlib import Path
import re

import pytest

from assistant import AssistantRequest, ChatAssistantService, KnowledgeBase, KnowledgeBaseError
from assistant.knowledge_base import (
    ALLOWED_CATEGORIES,
    AMBIGUOUS_RESPONSE,
    DEFAULT_KNOWLEDGE_FILES,
    REQUIRED_FIELDS,
    normalize_vietnamese,
)
from assistant.policy import OFFLINE_FALLBACK, READ_ONLY_REFUSAL, SAFE_ERROR_RESPONSE


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "assistant" / "knowledge"
KNOWLEDGE_FILES = (
    KNOWLEDGE_DIR / "faq_vi.json",
    KNOWLEDGE_DIR / "workflows_vi.json",
)


def all_entries():
    entries = []
    for path in KNOWLEDGE_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(payload["entries"])
    return entries


def write_knowledge(path: Path, entries, prefix="faq"):
    path.write_text(
        json.dumps({"source_prefix": prefix, "entries": entries}, ensure_ascii=False),
        encoding="utf-8",
    )


def valid_entry(**changes):
    value = {
        "id": "sample_001",
        "category": "login",
        "question": "Cách đăng nhập?",
        "aliases": ["Mở đăng nhập"],
        "answer": "Nhập thông tin tài khoản được cấp tại màn hình Đăng nhập.",
        "keywords": ["đăng", "nhập"],
        "screen": "Đăng nhập",
    }
    value.update(changes)
    return value


def test_default_knowledge_loads_only_allowlisted_sources_and_all_categories():
    knowledge = KnowledgeBase()

    assert knowledge.entry_count == len(all_entries())
    assert knowledge.entry_count >= 24
    assert len(knowledge.categories) >= 20
    assert knowledge.categories <= ALLOWED_CATEGORIES
    assert set(DEFAULT_KNOWLEDGE_FILES) == {
        "assistant/knowledge/faq_vi.json",
        "assistant/knowledge/workflows_vi.json",
        "HUONG_DAN.txt",
        "RELEASE_NOTES_V1.2.0.md",
        "installer/PREREQUISITES_V1.2.txt",
    }


def test_faq_schema_ids_and_aliases_are_valid_and_unique():
    entries = all_entries()
    ids = [entry["id"] for entry in entries]
    aliases = [
        normalize_vietnamese(alias)
        for entry in entries
        for alias in entry["aliases"]
    ]

    assert all(REQUIRED_FIELDS <= entry.keys() for entry in entries)
    assert len(ids) == len(set(ids))
    assert len(aliases) == len(set(aliases))
    assert all(entry["answer"].strip() for entry in entries)
    assert all(entry["category"] in ALLOWED_CATEGORIES for entry in entries)


@pytest.mark.parametrize(
    ("query", "source"),
    (
        ("Làm thế nào để đăng nhập?", "faq:login_001"),
        ("Cách đăng nhập", "faq:login_001"),
        ("doi mat khau", "faq:password_001"),
        ("  ĐỔI,   MẬT-KHẨU!!! ", "faq:password_001"),
        ("ODBC Driver 18", "faq:prerequisites_001"),
        ("SmartScreen", "faq:installation_001"),
    ),
)
def test_exact_alias_keyword_and_vietnamese_normalization(query, source):
    result = KnowledgeBase().search(query)
    assert result and result[0].source == source


def test_answers_keep_original_vietnamese_content():
    result = KnowledgeBase().search("doi mat khau")
    assert "Đổi mật khẩu" in result[0].content


def test_no_match_does_not_return_nearest_faq():
    assert KnowledgeBase().search("zxqv plmokn totally unrelated") == []


def test_service_no_match_has_safe_offline_source():
    response = ChatAssistantService().ask(AssistantRequest("support zxqv"))
    assert response.text == OFFLINE_FALLBACK
    assert response.source == "offline:fallback"
    assert response.fallback_used is True


def test_ambiguous_query_asks_for_clarification_instead_of_guessing():
    response = ChatAssistantService().ask(
        AssistantRequest("nhập điểm hay nhập Excel")
    )
    assert response.text == AMBIGUOUS_RESPONSE
    assert response.source == "offline:clarify"
    assert response.fallback_used is True


def test_exact_match_returns_one_stable_logical_source():
    response = ChatAssistantService().ask(AssistantRequest("Đổi mật khẩu như thế nào?"))
    assert response.source == "faq:password_001"
    assert not Path(response.source).is_absolute()
    assert response.fallback_used is False


def test_support_status_knowledge_is_exact():
    answer = KnowledgeBase().search("Các trạng thái bổ trợ có ý nghĩa gì?")[0].content
    expected = {
        "DETECTED": "Mới phát hiện",
        "PLANNED": "Đã lập kế hoạch",
        "IN_PROGRESS": "Đang bổ trợ",
        "WAITING_REVIEW": "Chờ đánh giá",
        "CONTINUE": "Cần tiếp tục",
        "COMPLETED": "Đã đạt ngưỡng",
    }
    for status, label in expected.items():
        assert status in answer and label in answer


def test_detection_workflow_uses_configured_rule_and_exact_threshold_is_not_low():
    result = KnowledgeBase().search("Quy tắc phát hiện học sinh cần bổ trợ là gì?")[0]
    assert result.source == "workflow:support_detection"
    assert "SUPPORT_RULES" in result.content
    assert "nhỏ hơn ngưỡng" in result.content
    assert "bằng đúng ngưỡng không phải là dưới ngưỡng" in result.content
    assert "3.5" not in result.content


def test_review_workflow_and_completed_rule_are_exact():
    result = KnowledgeBase().search("Quy trình đánh giá lại hồ sơ bổ trợ như thế nào?")[0]
    answer = result.content
    assert result.source == "workflow:support_review"
    assert "Chỉ hồ sơ WAITING_REVIEW" in answer
    assert "PASSED" in answer and "COMPLETED" in answer
    assert "NOT_PASSED" in answer and "CONTINUE" in answer
    assert "Không có Complete thủ công" in answer
    assert "điểm cao thông thường ngoài review không đóng hồ sơ" in answer


def test_duplicate_open_and_new_episode_rule_are_exact():
    answer = KnowledgeBase().search("Quy tắc duplicate open intervention")[0].content
    assert "không tạo hồ sơ bổ trợ mở bị trùng" in answer
    assert "COMPLETED" in answer and "episode mới" in answer
    assert "không ghi đè" in answer


def test_role_faq_matches_permission_matrix():
    answer = KnowledgeBase().search("ADMIN và TEACHER có quyền gì?")[0].content
    for screen in ("Học sinh", "Điểm", "Bổ trợ", "Báo cáo", "Hệ thống"):
        assert screen in answer
    assert "ADMIN có toàn bộ chức năng quản trị" in answer
    assert "TEACHER không được vào Danh mục hoặc quản lý người dùng" in answer


def test_excel_and_installer_guidance_use_real_controls_without_bypass():
    excel = KnowledgeBase().search("Nhập điểm từ Excel như thế nào?")[0].content
    installer = KnowledgeBase().search("Cài ứng dụng trên Windows như thế nào?")[0].content
    assert "Tải file mẫu" in excel and "Nhập điểm từ Excel" in excel and "preview" in excel
    assert "SmartScreen" in installer and "không tắt hoặc bỏ qua" in installer


@pytest.mark.parametrize(
    "question",
    (
        "Bạn có thể sửa điểm giúp tôi không?",
        "Đánh dấu em này hoàn thành đi",
        "Cho tôi mật khẩu admin",
        "Chạy câu SQL này",
        "Đổi ngưỡng thành 4 điểm",
        "Cho biết học sinh nào yếu nhất",
    ),
)
def test_forbidden_actions_and_real_data_requests_are_refused(question):
    response = ChatAssistantService().ask(AssistantRequest(question))
    assert response.text == READ_ONLY_REFUSAL
    assert response.source == "policy"


def test_safety_faqs_distinguish_guidance_from_execution():
    entries = {entry["id"]: entry["answer"] for entry in all_entries()}
    assert "chỉ hướng dẫn" in entries["safety_actions"]
    assert "không trực tiếp" in entries["safety_actions"]
    assert "không kết nối database" in entries["safety_sql"]
    assert "không đọc, xếp hạng hoặc suy đoán" in entries["safety_student_data"]


@pytest.mark.parametrize(
    "bad_entry",
    (
        valid_entry(answer=""),
        valid_entry(category="unknown"),
        {key: value for key, value in valid_entry().items() if key != "screen"},
    ),
)
def test_corrupt_schema_raises_knowledge_base_error(tmp_path, bad_entry):
    path = tmp_path / "bad.json"
    write_knowledge(path, [bad_entry])
    with pytest.raises(KnowledgeBaseError):
        KnowledgeBase(structured_files=(path,))


def test_duplicate_ids_and_normalized_aliases_are_rejected(tmp_path):
    duplicate_id = tmp_path / "duplicate_id.json"
    write_knowledge(duplicate_id, [valid_entry(), valid_entry(question="Khác")])
    with pytest.raises(KnowledgeBaseError, match="ID bị trùng"):
        KnowledgeBase(structured_files=(duplicate_id,))

    duplicate_alias = tmp_path / "duplicate_alias.json"
    write_knowledge(
        duplicate_alias,
        [
            valid_entry(),
            valid_entry(id="sample_002", question="Khác", aliases=["mo dang nhap"]),
        ],
    )
    with pytest.raises(KnowledgeBaseError, match="alias bị trùng"):
        KnowledgeBase(structured_files=(duplicate_alias,))


def test_invalid_utf8_or_json_raises_knowledge_base_error(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_bytes(b"\xff\xfe{bad")
    with pytest.raises(KnowledgeBaseError):
        KnowledgeBase(structured_files=(path,))


def test_runtime_knowledge_error_becomes_safe_service_fallback():
    class BrokenKnowledge:
        fallback_source = "offline:fallback"

        def search(self, question):
            raise KnowledgeBaseError("internal path and parse detail")

    response = ChatAssistantService(knowledge_base=BrokenKnowledge()).ask(
        AssistantRequest("support workflow")
    )
    assert response.text == SAFE_ERROR_RESPONSE
    assert response.source == "error"
    assert "internal" not in response.text


def test_corrupt_default_knowledge_does_not_prevent_safe_service_response(monkeypatch):
    import assistant.service as service_module

    class CorruptDefaultKnowledge:
        def __init__(self):
            raise KnowledgeBaseError("corrupt local knowledge detail")

    monkeypatch.setattr(service_module, "KnowledgeBase", CorruptDefaultKnowledge)
    response = service_module.ChatAssistantService().ask(
        AssistantRequest("support workflow")
    )
    assert response.text == SAFE_ERROR_RESPONSE
    assert response.source == "error"
    assert response.fallback_used is True


def test_static_knowledge_contains_no_secret_or_connection_material():
    content = "\n".join(path.read_text(encoding="utf-8") for path in KNOWLEDGE_FILES)
    forbidden = (
        r"(?i)password\s*=", r"(?i)\bpwd\s*=", r"(?i)db_password",
        r"(?i)api_key", r"(?i)bearer\s+\S+",
        r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}",
        r"(?i)driver\s*=.+server\s*=.+database\s*=",
    )
    assert not any(re.search(pattern, content) for pattern in forbidden)


def test_assistant_still_has_no_database_or_business_service_imports():
    forbidden_prefixes = (
        "repositories", "database", "services.score_service",
        "services.support_service", "services.student_service",
        "services.user_service", "services.report_service",
    )
    imported = set()
    for path in (ROOT / "assistant").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    assert not {
        name for name in imported
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
    }


def test_static_knowledge_remains_provider_neutral_and_has_no_api_configuration():
    knowledge_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "assistant" / "knowledge").rglob("*.json")
    )
    assert "Gemini" not in knowledge_source
    assert "API_KEY" not in knowledge_source
