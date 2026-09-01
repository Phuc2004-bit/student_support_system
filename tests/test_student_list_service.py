from services.student_list_service import StudentListService


def test_service_reads_student_list_in_one_transaction():
    connection = object()

    class Tx:
        def __enter__(self):
            return connection

        def __exit__(self, *args):
            return False

    class DB:
        def transaction(self):
            return Tx()

    class Repo:
        def __init__(self):
            self.connection = None
            self.filters = None

        def list_students(self, c, filters):
            self.connection = c
            self.filters = filters
            return ["row"]

    repo = Repo()
    service = StudentListService(DB(), repo)

    assert service.list_students() == ["row"]
    assert repo.connection is connection
    assert repo.filters is not None