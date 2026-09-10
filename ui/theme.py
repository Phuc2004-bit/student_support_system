"""Central presentation tokens for the V1.1 dark desktop interface."""

APP_BACKGROUND = "#0F172A"
SIDEBAR_BACKGROUND = "#111827"
SURFACE = "#1E293B"
SURFACE_HOVER = "#273449"
BORDER = "#334155"

PRIMARY = "#38BDF8"
PRIMARY_HOVER = "#0EA5E9"

TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"

SUCCESS = "#22C55E"
WARNING = "#F59E0B"
DANGER = "#EF4444"

PRIMARY_SUBTLE = "#173B52"
SUCCESS_SUBTLE = "#153D2B"
WARNING_SUBTLE = "#4A3515"
DANGER_SUBTLE = "#4A2028"

CHART_ACCENTS = (PRIMARY, WARNING, SUCCESS, "#A78BFA", "#F472B6", "#2DD4BF")


def main_window_stylesheet() -> str:
    """Return the shared stylesheet scoped to the application main window."""

    return f"""
    QMainWindow#mainWindow,
    QWidget#centralWidget,
    QWidget#contentShell,
    QWidget#bodyWidget,
    QStackedWidget#pageStack {{
        background-color: {APP_BACKGROUND};
        color: {TEXT_PRIMARY};
        font-family: "Segoe UI";
    }}

    QFrame#sidebar {{
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-right: 1px solid {BORDER};
    }}
    QLabel#sidebarBrandMark {{
        background-color: transparent;
        border: none;
        min-width: 38px;
        min-height: 38px;
        max-width: 38px;
        max-height: 38px;
    }}
    QLabel#sidebarBrandTitle {{
        color: {TEXT_PRIMARY};
        font-size: 16px;
        font-weight: 600;
    }}
    QLabel#sidebarBrandSubtitle,
    QLabel#sidebarRoleLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel[sidebarSection="true"] {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: 600;
        padding: 12px 8px 4px 8px;
    }}
    QMainWindow#mainWindow QPushButton[navItem="true"] {{
        color: {TEXT_SECONDARY};
        background-color: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 8px;
        min-height: 44px;
        padding: 0 12px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
    }}
    QMainWindow#mainWindow QPushButton[navItem="true"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE_HOVER};
    }}
    QMainWindow#mainWindow QPushButton[navItem="true"]:checked {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border-left: 3px solid {PRIMARY};
        font-weight: 600;
    }}
    QMainWindow#mainWindow QPushButton[navItem="true"]:focus {{
        border-left: 3px solid {PRIMARY};
    }}
    QFrame#sidebarUserBlock {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
    }}
    QLabel#sidebarAvatarLabel {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-radius: 17px;
        min-width: 34px;
        min-height: 34px;
        max-width: 34px;
        max-height: 34px;
        font-weight: 700;
    }}
    QLabel#sidebarUserLabel {{
        color: {TEXT_PRIMARY};
        font-size: 13px;
        font-weight: 600;
    }}

    QFrame#topbar {{
        background-color: {APP_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
    }}
    QLabel#appTitleLabel {{
        color: {TEXT_PRIMARY};
        font-size: 19px;
        font-weight: 600;
    }}
    QLabel#topbarSubtitleLabel,
    QLabel#roleLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel#userLabel {{
        color: {TEXT_PRIMARY};
        font-size: 13px;
        font-weight: 600;
    }}

    QMainWindow#mainWindow QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 34px;
        padding: 0 14px;
        font-size: 13px;
    }}
    QMainWindow#mainWindow QPushButton:hover {{
        background-color: {SURFACE_HOVER};
        border-color: {TEXT_MUTED};
    }}
    QMainWindow#mainWindow QPushButton:pressed {{
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {PRIMARY};
    }}
    QMainWindow#mainWindow QPushButton:focus {{
        border-color: {PRIMARY};
    }}
    QMainWindow#mainWindow QPushButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QMainWindow#mainWindow QPushButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QMainWindow#mainWindow QPushButton[variant="primary"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QMainWindow#mainWindow QPushButton[variant="danger"] {{
        color: {DANGER};
        background-color: transparent;
        border-color: {DANGER};
    }}
    QMainWindow#mainWindow QPushButton[variant="danger"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {DANGER};
    }}

    QWidget#dashboardPage,
    QWidget#dashboardScrollContents,
    QScrollArea#dashboardScrollArea,
    QScrollArea#dashboardScrollArea > QWidget > QWidget {{
        background-color: {APP_BACKGROUND};
        color: {TEXT_PRIMARY};
        border: none;
    }}
    QLabel#dashboardTitleLabel {{
        color: {TEXT_PRIMARY};
        font-size: 24px;
        font-weight: 700;
    }}
    QLabel#dashboardSubtitleLabel {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}
    QLabel#dashboardStateLabel {{
        color: {WARNING};
        font-size: 12px;
    }}
    QLabel#dashboardKpiTitleLabel,
    QLabel#dashboardFilterTitleLabel,
    QLabel#dashboardChartTitleLabel,
    QLabel#dashboardAttentionTitleLabel {{
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 600;
    }}
    QFrame#dashboardKpiFrame,
    QFrame#dashboardChartFrame {{
        background-color: transparent;
        border: none;
    }}
    QFrame#dashboardFilterFrame,
    QFrame#dashboardAttentionFrame {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QFrame[cardRole="kpi"] {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-top: 3px solid {PRIMARY};
        border-radius: 12px;
    }}
    QFrame[cardRole="kpi"][accent="warning"] {{ border-top-color: {WARNING}; }}
    QFrame[cardRole="kpi"][accent="success"] {{ border-top-color: {SUCCESS}; }}
    QFrame[cardRole="kpi"][accent="danger"] {{ border-top-color: {DANGER}; }}
    QLabel#kpiCardTitleLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 500;
    }}
    QLabel#kpiCardValueLabel {{
        color: {TEXT_PRIMARY};
        font-size: 27px;
        font-weight: 700;
    }}
    QWidget#dashboardBarChart,
    QWidget#dashboardDonutChart {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#dashboardAttentionEmptyLabel {{
        color: {TEXT_SECONDARY};
        background-color: transparent;
        min-height: 72px;
    }}

    QMainWindow#mainWindow QLabel {{ color: {TEXT_PRIMARY}; }}
    QMainWindow#mainWindow QLineEdit,
    QMainWindow#mainWindow QComboBox,
    QMainWindow#mainWindow QSpinBox,
    QMainWindow#mainWindow QDoubleSpinBox,
    QMainWindow#mainWindow QDateEdit,
    QMainWindow#mainWindow QTextEdit,
    QMainWindow#mainWindow QPlainTextEdit {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 34px;
        padding: 0 10px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QMainWindow#mainWindow QLineEdit:focus,
    QMainWindow#mainWindow QComboBox:focus,
    QMainWindow#mainWindow QSpinBox:focus,
    QMainWindow#mainWindow QDoubleSpinBox:focus,
    QMainWindow#mainWindow QDateEdit:focus,
    QMainWindow#mainWindow QTextEdit:focus,
    QMainWindow#mainWindow QPlainTextEdit:focus {{
        border-color: {PRIMARY};
    }}
    QMainWindow#mainWindow QComboBox:disabled,
    QMainWindow#mainWindow QLineEdit:disabled,
    QMainWindow#mainWindow QDateEdit:disabled,
    QMainWindow#mainWindow QSpinBox:disabled,
    QMainWindow#mainWindow QDoubleSpinBox:disabled,
    QMainWindow#mainWindow QTextEdit:disabled,
    QMainWindow#mainWindow QPlainTextEdit:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
    }}
    QMainWindow#mainWindow QComboBox QAbstractItemView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QMainWindow#mainWindow QTableWidget,
    QMainWindow#mainWindow QTableView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        gridline-color: {BORDER};
        selection-background-color: {PRIMARY_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QMainWindow#mainWindow QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    QMainWindow#mainWindow QTableCornerButton::section {{
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
    }}
    QMainWindow#mainWindow QTableWidget::item:hover {{ background-color: {SURFACE_HOVER}; }}
    QMainWindow#mainWindow QMenu {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        padding: 4px;
    }}
    QMainWindow#mainWindow QMenu::item {{ padding: 7px 18px; border-radius: 5px; }}
    QMainWindow#mainWindow QMenu::item:selected {{ background-color: {PRIMARY_HOVER}; }}
    QMainWindow#mainWindow QToolTip {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        padding: 5px 8px;
    }}
    QMainWindow#mainWindow QMessageBox {{ color: {TEXT_PRIMARY}; background-color: {APP_BACKGROUND}; }}
    QMainWindow#mainWindow QMessageBox QLabel {{ color: {TEXT_PRIMARY}; min-width: 260px; }}
    QMainWindow#mainWindow QCalendarWidget QWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
    }}
    QMainWindow#mainWindow QScrollBar:vertical {{
        background: {APP_BACKGROUND};
        width: 10px;
        margin: 0;
    }}
    QMainWindow#mainWindow QScrollBar::handle:vertical {{
        background: {BORDER};
        min-height: 28px;
        border-radius: 5px;
    }}
    QMainWindow#mainWindow QScrollBar::handle:vertical:hover {{
        background: {TEXT_MUTED};
    }}
    QMainWindow#mainWindow QScrollBar::add-line:vertical,
    QMainWindow#mainWindow QScrollBar::sub-line:vertical {{ height: 0; }}
    QMainWindow#mainWindow QScrollBar:horizontal {{
        background: {APP_BACKGROUND}; height: 10px; margin: 0;
    }}
    QMainWindow#mainWindow QScrollBar::handle:horizontal {{
        background: {BORDER}; min-width: 28px; border-radius: 5px;
    }}
    QMainWindow#mainWindow QScrollBar::handle:horizontal:hover {{ background: {TEXT_MUTED}; }}
    QMainWindow#mainWindow QScrollBar::add-line:horizontal,
    QMainWindow#mainWindow QScrollBar::sub-line:horizontal {{ width: 0; }}
    """


def student_page_stylesheet() -> str:
    """Styles used by StudentsPage, including standalone UI tests."""

    return f"""
    QWidget#studentsPage {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        font-family: "Segoe UI";
    }}
    QFrame#studentsToolbarFrame,
    QFrame#studentsTableCard,
    QFrame#studentsDetailsCard {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#studentsCountLabel,
    QLabel#studentsDetailsTitle,
    QLabel[studentFilterLabel="true"] {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#studentsEmptyTitle {{
        color: {TEXT_PRIMARY};
        font-size: 17px;
        font-weight: 600;
    }}
    QLabel#studentsEmptyDescription {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}
    QWidget#studentFilterWidget QLineEdit,
    QWidget#studentFilterWidget QComboBox {{
        color: {TEXT_PRIMARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 38px;
        padding: 0 10px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#studentFilterWidget QLineEdit:focus,
    QWidget#studentFilterWidget QComboBox:focus {{
        border-color: {PRIMARY};
    }}
    QWidget#studentFilterWidget QComboBox QAbstractItemView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#studentsPage QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE_HOVER};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 36px;
        padding: 0 14px;
        font-size: 13px;
    }}
    QWidget#studentsPage QPushButton:hover {{ border-color: {TEXT_MUTED}; }}
    QWidget#studentsPage QPushButton:focus {{ border-color: {PRIMARY}; }}
    QWidget#studentsPage QPushButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
    }}
    QWidget#studentsPage QPushButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QWidget#studentsPage QPushButton[variant="primary"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QWidget#studentsPage QTableWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: none;
        gridline-color: {BORDER};
        selection-background-color: {PRIMARY_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QWidget#studentsPage QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    QWidget#currentEnrollmentWidget,
    QWidget#enrollmentHistoryWidget {{
        color: {TEXT_PRIMARY};
        background-color: transparent;
    }}
    QLabel#currentEnrollmentHeading,
    QLabel#enrollmentHistoryHeading {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#currentEnrollmentClass {{
        color: {TEXT_PRIMARY};
        font-size: 18px;
        font-weight: 700;
    }}
    """


def scores_page_stylesheet() -> str:
    """Styles for the score-entry workspace using the shared V1.1 tokens."""

    return f"""
    QWidget#scoresPage {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        font-family: "Segoe UI";
    }}
    QFrame#scoresToolbarCard,
    QFrame#assessmentInfoCard,
    QFrame#scoreTablePlaceholder {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel[scoreFilterLabel="true"],
    QLabel#assessmentInfoCaption,
    QLabel#scoreTableCaption {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#assessmentInfoName {{
        color: {TEXT_PRIMARY};
        font-size: 17px;
        font-weight: 700;
    }}
    QLabel#assessmentInfoMeta,
    QLabel#scoreContextStatus {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel#assessmentStatusBadge {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#assessmentStatusBadge[assessmentStatus="ACTIVE"] {{
        color: {SUCCESS};
        background-color: {SUCCESS_SUBTLE};
        border-color: {SUCCESS};
    }}
    QLabel#assessmentStatusBadge[assessmentStatus="LOCKED"] {{
        color: {WARNING};
        background-color: {WARNING_SUBTLE};
        border-color: {WARNING};
    }}
    QLabel#assessmentStatusBadge[assessmentStatus="CANCELLED"] {{
        color: {DANGER};
        background-color: {DANGER_SUBTLE};
        border-color: {DANGER};
    }}
    QLabel#scoreUnsavedState {{
        color: {WARNING};
        background-color: {WARNING_SUBTLE};
        border: 1px solid {WARNING};
        border-radius: 7px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#scoreEmptyTitle {{
        color: {TEXT_PRIMARY};
        font-size: 17px;
        font-weight: 600;
    }}
    QLabel#scoreEmptyDescription {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}
    QWidget#scoreContextFilterWidget QComboBox {{
        color: {TEXT_PRIMARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 38px;
        padding: 0 10px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#scoreContextFilterWidget QComboBox:focus {{
        border-color: {PRIMARY};
    }}
    QWidget#scoreContextFilterWidget QComboBox:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
    }}
    QWidget#scoreContextFilterWidget QComboBox QAbstractItemView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#scoresPage QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE_HOVER};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 36px;
        padding: 0 14px;
        font-size: 13px;
    }}
    QWidget#scoresPage QPushButton:hover {{ border-color: {TEXT_MUTED}; }}
    QWidget#scoresPage QPushButton:focus {{ border-color: {PRIMARY}; }}
    QWidget#scoresPage QPushButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QWidget#scoresPage QPushButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QWidget#scoresPage QPushButton[variant="primary"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QWidget#scoresPage QPushButton[variant="primary"]:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QWidget#scoresPage QTableWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: none;
        gridline-color: {BORDER};
        selection-background-color: {PRIMARY_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QWidget#scoresPage QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    """


def support_page_stylesheet() -> str:
    """Styles for the support workflow workspace and its saved states."""

    return f"""
    QWidget#supportPage {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        font-family: "Segoe UI";
    }}
    QFrame#supportFilterCard,
    QFrame#supportTableFrame {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#supportFilterCaption,
    QLabel#supportTableCaption,
    QLabel[supportFilterLabel="true"] {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#supportCountLabel,
    QLabel#supportStateLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel#supportEmptyTitle {{
        color: {TEXT_PRIMARY};
        font-size: 17px;
        font-weight: 600;
    }}
    QLabel#supportEmptyDescription {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}
    QWidget#supportFilterWidget QComboBox {{
        color: {TEXT_PRIMARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 38px;
        padding: 0 10px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#supportFilterWidget QComboBox:focus {{ border-color: {PRIMARY}; }}
    QWidget#supportFilterWidget QComboBox:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
    }}
    QWidget#supportFilterWidget QComboBox QAbstractItemView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#supportPage QPushButton,
    QWidget#supportPage QToolButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE_HOVER};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 36px;
        padding: 0 14px;
        font-size: 13px;
    }}
    QWidget#supportPage QPushButton:hover,
    QWidget#supportPage QToolButton:hover {{ border-color: {TEXT_MUTED}; }}
    QWidget#supportPage QPushButton:focus,
    QWidget#supportPage QToolButton:focus {{ border-color: {PRIMARY}; }}
    QWidget#supportPage QPushButton:disabled,
    QWidget#supportPage QToolButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QWidget#supportPage QToolButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QWidget#supportPage QToolButton[variant="primary"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QWidget#supportPage QTableWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: none;
        gridline-color: {BORDER};
        selection-background-color: {PRIMARY_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QWidget#supportPage QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    """


def support_dialog_stylesheet() -> str:
    """Extend the shared dialog theme for support workflow details."""

    return dialog_stylesheet() + f"""
    QFrame#interventionIdentityCard,
    QFrame#interventionWorkflowCard,
    QFrame#interventionReviewCard {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#interventionStudentName {{
        color: {TEXT_PRIMARY};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#interventionStudentContext,
    QLabel#interventionWorkflowMessage,
    QLabel#interventionReviewEmpty {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel#interventionStatusBadge {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#interventionStatusBadge[interventionStatus="DETECTED"],
    QLabel#interventionStatusBadge[interventionStatus="WAITING_REVIEW"] {{
        color: {WARNING}; background-color: {WARNING_SUBTLE}; border-color: {WARNING};
    }}
    QLabel#interventionStatusBadge[interventionStatus="PLANNED"],
    QLabel#interventionStatusBadge[interventionStatus="IN_PROGRESS"] {{
        color: {PRIMARY}; background-color: {PRIMARY_SUBTLE}; border-color: {PRIMARY};
    }}
    QLabel#interventionStatusBadge[interventionStatus="CONTINUE"] {{
        color: {DANGER}; background-color: {DANGER_SUBTLE}; border-color: {DANGER};
    }}
    QLabel#interventionStatusBadge[interventionStatus="COMPLETED"] {{
        color: {SUCCESS}; background-color: {SUCCESS_SUBTLE}; border-color: {SUCCESS};
    }}
    QLabel[workflowStep="true"] {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel[workflowState="done"] {{ color: {SUCCESS}; border-color: {SUCCESS}; }}
    QLabel[workflowState="current"] {{
        color: {PRIMARY}; background-color: {PRIMARY_SUBTLE}; border-color: {PRIMARY};
    }}
    QLabel[workflowState="attention"] {{
        color: {WARNING}; background-color: {WARNING_SUBTLE}; border-color: {WARNING};
    }}
    QLabel[workflowState="complete"] {{
        color: {SUCCESS}; background-color: {SUCCESS_SUBTLE}; border-color: {SUCCESS};
    }}
    QLabel#interventionCompletedMessage {{
        color: {SUCCESS};
        background-color: {SUCCESS_SUBTLE};
        border: 1px solid {SUCCESS};
        border-radius: 8px;
        padding: 9px 12px;
        font-weight: 600;
    }}
    QLabel#interventionContinueMessage {{
        color: {WARNING};
        background-color: {WARNING_SUBTLE};
        border: 1px solid {WARNING};
        border-radius: 8px;
        padding: 9px 12px;
        font-weight: 600;
    }}
    QDialog#interventionDetailDialog QGroupBox {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        margin-top: 10px;
        padding: 12px;
        font-weight: 600;
    }}
    QDialog#interventionDetailDialog QGroupBox::title {{
        color: {TEXT_SECONDARY};
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 5px;
    }}
    """


def reports_page_stylesheet() -> str:
    """Styles for report filters, KPIs, charts, and detailed rows."""

    return f"""
    QWidget#reportsPage,
    QWidget#reportsScrollContents,
    QScrollArea#reportsScrollArea,
    QScrollArea#reportsScrollArea > QWidget > QWidget {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        border: none;
        font-family: "Segoe UI";
    }}
    QFrame#reportFilterCard,
    QFrame#reportSummaryFrame,
    QFrame#reportChartsFrame,
    QFrame#reportCasesFrame {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#reportFilterCaption,
    QLabel#reportSectionTitle,
    QLabel[supportFilterLabel="true"] {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#reportStateLabel,
    QLabel#reportRowCountLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel#reportEmptyTitle {{
        color: {TEXT_PRIMARY};
        font-size: 17px;
        font-weight: 600;
    }}
    QLabel#reportEmptyDescription {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}
    QWidget#reportsPage QFrame[cardRole="kpi"] {{
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-top: 3px solid {PRIMARY};
        border-radius: 10px;
    }}
    QWidget#reportsPage QFrame[cardRole="kpi"][accent="warning"] {{
        border-top-color: {WARNING};
    }}
    QWidget#reportsPage QFrame[cardRole="kpi"][accent="success"] {{
        border-top-color: {SUCCESS};
    }}
    QWidget#reportsPage QFrame[cardRole="kpi"][accent="danger"] {{
        border-top-color: {DANGER};
    }}
    QWidget#reportsPage QLabel#kpiCardTitleLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
        font-weight: 500;
    }}
    QWidget#reportsPage QLabel#kpiCardValueLabel {{
        color: {TEXT_PRIMARY};
        font-size: 25px;
        font-weight: 700;
    }}
    QWidget#reportsPage QWidget#reportStatusChart,
    QWidget#reportsPage QWidget#reportSubjectChart {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
    }}
    QWidget#reportsPage QWidget#supportFilterWidget QComboBox {{
        color: {TEXT_PRIMARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 38px;
        padding: 0 10px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#reportsPage QWidget#supportFilterWidget QComboBox:focus {{
        border-color: {PRIMARY};
    }}
    QWidget#reportsPage QWidget#supportFilterWidget QComboBox:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
    }}
    QWidget#reportsPage QWidget#supportFilterWidget QComboBox QAbstractItemView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QWidget#reportsPage QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE_HOVER};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 36px;
        padding: 0 14px;
        font-size: 13px;
    }}
    QWidget#reportsPage QPushButton:hover {{ border-color: {TEXT_MUTED}; }}
    QWidget#reportsPage QPushButton:focus {{ border-color: {PRIMARY}; }}
    QWidget#reportsPage QPushButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QWidget#reportsPage QPushButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QWidget#reportsPage QPushButton[variant="primary"]:hover {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QWidget#reportsPage QTableWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: none;
        gridline-color: {BORDER};
        selection-background-color: {PRIMARY_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QWidget#reportsPage QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    QWidget#reportsPage QScrollBar:vertical {{
        background: {APP_BACKGROUND};
        width: 10px;
        margin: 0;
    }}
    QWidget#reportsPage QScrollBar::handle:vertical {{
        background: {BORDER};
        min-height: 28px;
        border-radius: 5px;
    }}
    QWidget#reportsPage QScrollBar::add-line:vertical,
    QWidget#reportsPage QScrollBar::sub-line:vertical {{ height: 0; }}
    """


def catalog_system_stylesheet() -> str:
    """Styles for catalog maintenance and account administration pages."""

    return f"""
    QWidget#catalogPage,
    QWidget#systemPage {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        font-family: "Segoe UI";
    }}
    QLabel#catalogTitleLabel,
    QLabel#systemTitleLabel {{
        color: {TEXT_PRIMARY};
        font-size: 22px;
        font-weight: 700;
    }}
    QLabel#catalogSubtitleLabel,
    QLabel#systemSubtitleLabel,
    QLabel#catalogStateLabel,
    QLabel#systemStateLabel,
    QLabel#catalogGroupLabel,
    QLabel#catalogEmptyLabel,
    QLabel#systemEmptyLabel,
    QLabel#profileMetaLabel {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QLabel#catalogGroupLabel {{ font-weight: 600; }}
    QLabel#supportRuleExplanation {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 9px 12px;
    }}
    QFrame#catalogSectionCard,
    QFrame#profileCard,
    QFrame#usersCard {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#profileAvatarLabel {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-radius: 24px;
        min-width: 48px;
        min-height: 48px;
        max-width: 48px;
        max-height: 48px;
        font-size: 16px;
        font-weight: 700;
    }}
    QLabel#profileNameLabel {{
        color: {TEXT_PRIMARY};
        font-size: 18px;
        font-weight: 700;
    }}
    QWidget#catalogPage QTabWidget::pane,
    QWidget#systemPage QTabWidget::pane {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        top: -1px;
    }}
    QWidget#catalogPage QTabBar::tab,
    QWidget#systemPage QTabBar::tab {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        padding: 9px 14px;
        min-width: 100px;
    }}
    QWidget#catalogPage QTabBar::tab:selected,
    QWidget#systemPage QTabBar::tab:selected {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border-bottom: 2px solid {PRIMARY};
        font-weight: 600;
    }}
    QWidget#catalogPage QTabBar::tab:hover:!selected,
    QWidget#systemPage QTabBar::tab:hover:!selected {{ background-color: {SURFACE_HOVER}; }}
    QWidget#catalogPage QPushButton,
    QWidget#systemPage QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE_HOVER};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 34px;
        padding: 0 13px;
    }}
    QWidget#catalogPage QPushButton:hover,
    QWidget#systemPage QPushButton:hover {{ border-color: {TEXT_MUTED}; }}
    QWidget#catalogPage QPushButton[variant="primary"],
    QWidget#systemPage QPushButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QWidget#catalogPage QComboBox,
    QWidget#catalogPage QSpinBox,
    QWidget#systemPage QLineEdit {{
        color: {TEXT_PRIMARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 34px;
        padding: 0 10px;
    }}
    QWidget#catalogPage QComboBox:focus,
    QWidget#catalogPage QSpinBox:focus,
    QWidget#systemPage QLineEdit:focus {{ border-color: {PRIMARY}; }}
    QWidget#catalogPage QTableWidget,
    QWidget#systemPage QTableWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: none;
        gridline-color: transparent;
        selection-background-color: {PRIMARY_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QWidget#catalogPage QHeaderView::section,
    QWidget#systemPage QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    """


def dialog_stylesheet() -> str:
    """Shared dark styling for student and enrollment dialogs."""

    return f"""
    QDialog {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        font-family: "Segoe UI";
        font-size: 13px;
    }}
    QDialog QLabel {{ color: {TEXT_PRIMARY}; }}
    QLabel[dialogTitle="true"] {{
        color: {TEXT_PRIMARY};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel[dialogSubtitle="true"] {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    QFrame[dialogCard="true"],
    QWidget[profileTabContent="true"] {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QDialog QLineEdit,
    QDialog QComboBox,
    QDialog QDateEdit,
    QDialog QSpinBox,
    QDialog QDoubleSpinBox,
    QDialog QTextEdit,
    QDialog QPlainTextEdit {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 36px;
        padding: 0 10px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QDialog QTextEdit,
    QDialog QPlainTextEdit {{ padding: 8px 10px; }}
    QDialog QCheckBox {{
        color: {TEXT_PRIMARY};
        spacing: 8px;
    }}
    QDialog QLineEdit:focus,
    QDialog QComboBox:focus,
    QDialog QDateEdit:focus,
    QDialog QSpinBox:focus,
    QDialog QDoubleSpinBox:focus,
    QDialog QTextEdit:focus,
    QDialog QPlainTextEdit:focus {{ border-color: {PRIMARY}; }}
    QDialog QLineEdit:disabled,
    QDialog QComboBox:disabled,
    QDialog QDateEdit:disabled,
    QDialog QSpinBox:disabled,
    QDialog QDoubleSpinBox:disabled,
    QDialog QTextEdit:disabled,
    QDialog QPlainTextEdit:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
    }}
    QDialog QComboBox QAbstractItemView {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QDialog QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 36px;
        padding: 0 16px;
    }}
    QDialog QPushButton:hover {{
        background-color: {SURFACE_HOVER};
        border-color: {TEXT_MUTED};
    }}
    QDialog QPushButton:pressed {{
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {PRIMARY};
    }}
    QDialog QPushButton:focus {{ border-color: {PRIMARY}; }}
    QDialog QPushButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QDialog QPushButton[variant="danger"] {{
        color: {DANGER};
        background-color: transparent;
        border-color: {DANGER};
    }}
    QDialog QPushButton[variant="primary"],
    QDialog QPushButton#primaryDialogButton {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 600;
    }}
    QDialog QPushButton[variant="primary"]:hover,
    QDialog QPushButton#primaryDialogButton:hover {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QDialog QPushButton[variant="primary"]:disabled,
    QDialog QPushButton#primaryDialogButton:disabled {{
        color: {TEXT_MUTED};
        background-color: {SIDEBAR_BACKGROUND};
        border-color: {BORDER};
    }}
    QTabWidget::pane {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        top: -1px;
    }}
    QTabWidget::tab-bar {{ left: 0; }}
    QTabBar {{ background-color: transparent; }}
    QTabBar::tab {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        padding: 10px 16px;
        min-width: 110px;
    }}
    QTabBar::tab:selected {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border-bottom: 2px solid {PRIMARY};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{ background-color: {SURFACE_HOVER}; }}
    QDialog QTableWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
        border: none;
        gridline-color: {BORDER};
        selection-background-color: {PRIMARY_HOVER};
    }}
    QDialog QHeaderView::section {{
        color: {TEXT_SECONDARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 8px;
        font-weight: 600;
    }}
    QDialog QTableCornerButton::section {{
        background-color: {SIDEBAR_BACKGROUND};
        border: none;
        border-bottom: 1px solid {BORDER};
    }}
    QDialog QTableWidget::item:hover {{ background-color: {SURFACE_HOVER}; }}
    QDialog QScrollBar:vertical {{ background: {APP_BACKGROUND}; width: 10px; }}
    QDialog QScrollBar::handle:vertical {{
        background: {BORDER}; min-height: 28px; border-radius: 5px;
    }}
    QDialog QScrollBar:horizontal {{ background: {APP_BACKGROUND}; height: 10px; }}
    QDialog QScrollBar::handle:horizontal {{
        background: {BORDER}; min-width: 28px; border-radius: 5px;
    }}
    QDialog QScrollBar::handle:hover {{ background: {TEXT_MUTED}; }}
    QDialog QScrollBar::add-line,
    QDialog QScrollBar::sub-line {{ width: 0; height: 0; }}
    QDialog QCalendarWidget QWidget {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        alternate-background-color: {SIDEBAR_BACKGROUND};
    }}
    QLabel#studentProfileAvatar {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-radius: 25px;
        min-width: 50px;
        min-height: 50px;
        max-width: 50px;
        max-height: 50px;
        font-size: 16px;
        font-weight: 700;
    }}
    QLabel#studentProfileName {{
        color: {TEXT_PRIMARY};
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#studentProfileContext {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}
    """


def login_dialog_stylesheet() -> str:
    """Focused first-run styling for the authentication dialog."""

    return dialog_stylesheet() + f"""
    QDialog#loginDialog QFrame#loginCard {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 14px;
    }}
    QDialog#loginDialog QLabel#loginBrandMark {{
        background-color: transparent;
        border: none;
        min-width: 44px;
        min-height: 44px;
        max-width: 44px;
        max-height: 44px;
    }}
    QDialog#loginDialog QLabel#loginTitleLabel {{
        color: {TEXT_PRIMARY}; font-size: 19px; font-weight: 700;
    }}
    QDialog#loginDialog QLabel#loginSubtitleLabel {{
        color: {TEXT_SECONDARY}; font-size: 12px;
    }}
    QDialog#loginDialog QLabel#error_label {{
        color: {DANGER};
        background-color: {DANGER_SUBTLE};
        border: 1px solid {DANGER};
        border-radius: 7px;
        padding: 7px 10px;
    }}
    """


def chat_assistant_stylesheet() -> str:
    """Central dark-theme styling for the read-only assistant dialog."""

    return f"""
    QDialog#chatAssistantDialog,
    QWidget#chatAssistantWidget,
    QWidget#chatMessageContainer {{
        color: {TEXT_PRIMARY};
        background-color: {APP_BACKGROUND};
        font-family: "Segoe UI";
    }}
    QFrame#chatHeader {{
        background-color: {SURFACE};
        border: none;
        border-bottom: 1px solid {BORDER};
    }}
    QLabel#chatTitleLabel {{
        color: {TEXT_PRIMARY};
        font-size: 16px;
        font-weight: 700;
    }}
    QLabel#chatSubtitleLabel,
    QLabel#chatSafetyLabel,
    QLabel#chatSourceLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}
    QLabel#chatOfflineBadge {{
        color: {SUCCESS};
        background-color: {SUCCESS_SUBTLE};
        border: 1px solid {SUCCESS};
        border-radius: 8px;
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    QScrollArea#chatScrollArea {{
        background-color: {APP_BACKGROUND};
        border: none;
    }}
    QFrame#chatUserBubble {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_SUBTLE};
        border: 1px solid {PRIMARY};
        border-radius: 12px;
    }}
    QFrame#chatAssistantBubble {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    QLabel#chatMessageText,
    QLabel#chatWelcomeLabel {{
        color: {TEXT_PRIMARY};
        font-size: 13px;
    }}
    QFrame#chatComposer {{
        background-color: {SURFACE};
        border: none;
        border-top: 1px solid {BORDER};
    }}
    QPlainTextEdit#chatInput {{
        color: {TEXT_PRIMARY};
        background-color: {SIDEBAR_BACKGROUND};
        border: 1px solid {BORDER};
        border-radius: 9px;
        padding: 7px 9px;
        selection-background-color: {PRIMARY_HOVER};
    }}
    QPlainTextEdit#chatInput:focus {{ border-color: {PRIMARY}; }}
    QPushButton {{
        color: {TEXT_PRIMARY};
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        min-height: 32px;
        padding: 0 10px;
    }}
    QPushButton:hover {{ background-color: {SURFACE_HOVER}; }}
    QPushButton:focus {{ border-color: {PRIMARY}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; background-color: {SIDEBAR_BACKGROUND}; }}
    QPushButton[variant="primary"] {{
        color: {SIDEBAR_BACKGROUND};
        background-color: {PRIMARY};
        border-color: {PRIMARY};
        font-weight: 700;
    }}
    QPushButton[quickAction="true"] {{
        color: {PRIMARY};
        background-color: {SURFACE};
        border-color: {BORDER};
        text-align: left;
    }}
    QScrollBar:vertical {{
        background: {APP_BACKGROUND};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{ height: 0; }}
    """


def status_badge_colors(status: object) -> tuple[str, str]:
    """Return accessible foreground/background colors for a saved status."""

    value = str(getattr(status, "value", status))
    palette = {
        "ACTIVE": (SUCCESS, SUCCESS_SUBTLE),
        "INACTIVE": (TEXT_SECONDARY, SIDEBAR_BACKGROUND),
        "LOCKED": (WARNING, WARNING_SUBTLE),
        "CANCELLED": (TEXT_SECONDARY, SIDEBAR_BACKGROUND),
        "DETECTED": (WARNING, WARNING_SUBTLE),
        "PLANNED": (PRIMARY, PRIMARY_SUBTLE),
        "IN_PROGRESS": (PRIMARY, PRIMARY_SUBTLE),
        "WAITING_REVIEW": (WARNING, WARNING_SUBTLE),
        "CONTINUE": (DANGER, DANGER_SUBTLE),
        "COMPLETED": (SUCCESS, SUCCESS_SUBTLE),
        "TRANSFERRED": (TEXT_SECONDARY, SIDEBAR_BACKGROUND),
        "VALID": (SUCCESS, SUCCESS_SUBTLE),
        "WARNING": (WARNING, WARNING_SUBTLE),
        "ERROR": (DANGER, DANGER_SUBTLE),
    }
    return palette.get(value, (TEXT_SECONDARY, SIDEBAR_BACKGROUND))
