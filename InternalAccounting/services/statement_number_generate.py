from models import Statements


class StatementNumber:
    @staticmethod
    def generate_statement_number(statement_year):
        last_statement = Statements.objects.select_for_update().filter(
            statement_year=statement_year
        ).order_by('-statement_number').first()

        statement_number = (last_statement.statement_number + 1) if last_statement else 1

        return statement_number