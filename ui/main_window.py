from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app_context import AppContext
from ui.pages.dashboard_page import DashboardPage
from ui.pages.placeholder_page import PlaceholderPage
from ui.pages.students_page import StudentsPage
from ui.pages.scores_page import ScoresPage
from ui.pages.support_page import SupportPage
from ui.widgets.page_stack import PageStack
from ui.widgets.sidebar import Sidebar
from ui.widgets.topbar import Topbar


class MainWindow(QMainWindow):
    """
    Cửa sổ chính.

    Đăng ký các page nghiệp vụ đã được triển khai và giữ placeholder
    cho các khu vực chưa xây dựng.
    """

    logout_requested = Signal()
    window_closed = Signal()

    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 800
    SIDEBAR_WIDTH = 240
    TOPBAR_HEIGHT = Topbar.HEIGHT

    PAGE_TITLES = {
        "dashboard": "Tổng quan",
        "students": "Học sinh",
        "scores": "Điểm & Đánh giá",
        "support": "Bổ trợ học tập",
        "reports": "Báo cáo & Thống kê",
        "catalogs": "Danh mục",
        "system": "Hệ thống",
    }

    def __init__(
        self,
        app_context: AppContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if app_context is None:
            raise ValueError(
                "AppContext không được để trống."
            )

        if not app_context.is_authenticated:
            raise PermissionError(
                "Không thể mở MainWindow khi chưa đăng nhập."
            )

        self.app_context = app_context
        self._logout_in_progress = False

        self.setObjectName("mainWindow")
        self.setWindowTitle(
            "Hệ thống quản lý học sinh cần bổ trợ"
        )
        self.resize(
            self.DEFAULT_WIDTH,
            self.DEFAULT_HEIGHT,
        )

        self._build_ui()
        self._register_pages()
        self._connect_signals()
        self._apply_navigation_permissions()

        self.navigate_to("dashboard")
        self._initialize_dashboard()

    def _build_ui(self) -> None:
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName(
            "centralWidget"
        )
        self.setCentralWidget(
            self.central_widget
        )

        root_layout = QVBoxLayout(
            self.central_widget
        )
        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root_layout.setSpacing(0)

        self.topbar = Topbar(
            self.app_context.session,
            self.central_widget,
        )
        root_layout.addWidget(self.topbar)

        body_widget = QWidget(
            self.central_widget
        )
        body_widget.setObjectName(
            "bodyWidget"
        )

        body_layout = QHBoxLayout(
            body_widget
        )
        body_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        body_layout.setSpacing(0)

        self.sidebar = Sidebar(
            body_widget
        )
        self.sidebar.setFixedWidth(
            self.SIDEBAR_WIDTH
        )
        body_layout.addWidget(
            self.sidebar
        )

        self.page_stack = PageStack(
            body_widget
        )
        body_layout.addWidget(
            self.page_stack,
            1,
        )

        root_layout.addWidget(
            body_widget,
            1,
        )

    def _register_pages(self) -> None:
        self.pages: dict[str, QWidget] = {}

        dashboard_page = DashboardPage(
            academic_service=self.app_context.academic_service,
            dashboard_service=self.app_context.dashboard_service,
            parent=self.page_stack,
        )
        self.pages["dashboard"] = (
            dashboard_page
        )
        self.page_stack.register_page(
            "dashboard",
            dashboard_page,
        )

        students_page = StudentsPage(
            student_service=self.app_context.student_list_service,
            academic_service=self.app_context.academic_service,
            student_crud_service=self.app_context.student_service,
            enrollment_service=self.app_context.enrollment_service,
            student_profile_service=(
                self.app_context.student_profile_service
            ),
            parent=self.page_stack,
        )
        self.pages["students"] = students_page
        self.page_stack.register_page(
            "students",
            students_page,
        )

        scores_page = ScoresPage(
            academic_service=self.app_context.academic_service,
            enrollment_service=self.app_context.enrollment_service,
            score_service=self.app_context.score_service,
            parent=self.page_stack,
        )
        self.pages["scores"] = scores_page
        self.page_stack.register_page(
            "scores",
            scores_page,
        )

        support_page = SupportPage(
            academic_service=self.app_context.academic_service,
            support_read_service=self.app_context.report_service,
            intervention_detail_service=self.app_context.support_service,
            intervention_planning_service=self.app_context.support_service,
            intervention_start_service=self.app_context.support_service,
            intervention_waiting_review_service=(
                self.app_context.support_service
            ),
            intervention_review_service=self.app_context.support_service,
            intervention_continue_service=self.app_context.support_service,
            assessment_service=self.app_context.academic_service,
            user_service=self.app_context.user_service,
            parent=self.page_stack,
        )
        self.pages["support"] = support_page
        self.page_stack.register_page(
            "support",
            support_page,
        )

        for key, title in self.PAGE_TITLES.items():
            if key in {"dashboard", "students", "scores", "support"}:
                continue

            page = PlaceholderPage(
                title,
                self.page_stack,
            )
            self.pages[key] = page
            self.page_stack.register_page(
                key,
                page,
            )

    def _initialize_dashboard(self) -> None:
        dashboard_page = self.pages.get("dashboard")
        if isinstance(dashboard_page, DashboardPage):
            dashboard_page.initialize_dashboard()

    def _connect_signals(self) -> None:
        self.sidebar.navigation_requested.connect(
            self.navigate_to
        )
        self.topbar.logout_requested.connect(
            self.request_logout
        )

    def _apply_navigation_permissions(self) -> None:
        permissions = {
            "dashboard": True,
            "students": self.app_context.can_manage_students(),
            "scores": self.app_context.can_manage_scores(),
            "support": self.app_context.can_manage_support(),
            "reports": self.app_context.can_view_reports(),
            "catalogs": self.app_context.can_manage_catalogs(),
            "system": self.app_context.can_manage_users(),
        }

        self._navigation_permissions = permissions

        for key, allowed in permissions.items():
            self.sidebar.set_item_visible(
                key,
                allowed,
            )

    def can_navigate_to(
        self,
        key: str,
    ) -> bool:
        if key not in self.PAGE_TITLES:
            raise KeyError(
                f"Không tồn tại page: {key}"
            )

        return bool(
            self._navigation_permissions.get(
                key,
                False,
            )
        )

    def navigate_to(
        self,
        key: str,
    ) -> None:
        if not self.can_navigate_to(key):
            raise PermissionError(
                f"Không có quyền truy cập page: {key}"
            )

        self.page_stack.show_page(key)
        self.sidebar.set_current_item(key)

        if key == "students":
            self._initialize_students()
        elif key == "scores":
            self._initialize_scores()
        elif key == "support":
            self._initialize_support()

    def _initialize_students(self) -> None:
        students_page = self.pages.get("students")
        if isinstance(students_page, StudentsPage):
            students_page.initialize_students()

    def _initialize_scores(self) -> None:
        scores_page = self.pages.get("scores")
        if isinstance(scores_page, ScoresPage):
            scores_page.initialize_scores()

    def _initialize_support(self) -> None:
        support_page = self.pages.get("support")
        if isinstance(support_page, SupportPage):
            support_page.initialize_support()

    def request_logout(self) -> None:
        if self._logout_in_progress:
            return

        self._logout_in_progress = True
        self.app_context.clear_session()
        self.logout_requested.emit()
        self.close()

    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.window_closed.emit()
        super().closeEvent(event)
