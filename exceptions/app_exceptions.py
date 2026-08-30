class AppError(Exception):
    """Lớp cha cho các lỗi nghiệp vụ của ứng dụng."""


class ValidationError(AppError):
    """Dữ liệu đầu vào không hợp lệ."""


class NotFoundError(AppError):
    """Không tìm thấy dữ liệu được yêu cầu."""


class DuplicateError(AppError):
    """Dữ liệu bị trùng theo quy tắc nghiệp vụ."""


class AuthenticationError(AppError):
    """Đăng nhập hoặc xác thực không hợp lệ."""


class PermissionDeniedError(AppError):
    """Người dùng không có quyền thực hiện thao tác."""


class BusinessRuleError(AppError):
    """Vi phạm quy tắc nghiệp vụ của hệ thống."""


class InvalidStateTransitionError(BusinessRuleError):
    """Chuyển trạng thái hồ sơ bổ trợ không hợp lệ."""


class MissingSupportRuleError(BusinessRuleError):
    """Không tìm thấy quy tắc/ngưỡng bổ trợ phù hợp."""


class DatabaseError(AppError):
    """Lỗi thao tác với cơ sở dữ liệu."""