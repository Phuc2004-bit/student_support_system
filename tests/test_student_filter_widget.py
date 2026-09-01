import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from ui.widgets.student_filter_widget import StudentFilterWidget

def app(): return QApplication.instance() or QApplication([])

class Academic:
    def list_school_years(self): return [(2,"2026-2027",None,None,True),(1,"2025-2026",None,None,False)]
    def list_grades(self): return [(6,6,"Khối 6"),(7,7,"Khối 7")]
    def list_classes_by_school_year(self,year_id): return [(61,"6A1",6,True),(71,"7A1",7,True)]

def test_loads_current_year_and_dependent_classes():
    app(); w=StudentFilterWidget(Academic()); w.load_options()
    assert w.school_year_combo.currentData()==2
    assert w.class_combo.count()==3
    w.grade_combo.setCurrentIndex(1)
    assert w.class_combo.count()==2
    assert w.class_combo.itemText(1)=="6A1"

def test_current_value_contains_selected_filters():
    app(); w=StudentFilterWidget(Academic()); w.load_options()
    w.search_input.setText("HS01"); w.grade_combo.setCurrentIndex(2); w.class_combo.setCurrentIndex(1)
    value=w.current_value()
    assert value.search_text=="HS01"
    assert value.school_year_id==2
    assert value.grade_id==7
    assert value.class_id==71
