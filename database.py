from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Employee(db.Model):
    __tablename__ = 'employees'
    
    employee_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False, index=True)
    position = db.Column(db.String(100), nullable=False)
    hire_date = db.Column(db.Date, nullable=False)
    salary = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Внешний ключ на самого себя
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.employee_id", ondelete='SET NULL'))
    
    # Связь: позволяет обращаться к начальнику (emp.manager) и подчиненным (emp.subordinates)
    subordinates = relationship(
        "Employee", 
        backref=db.backref('manager', remote_side=[employee_id])
    )

    def __repr__(self):
        return f"<Employee {self.full_name} ({self.position})>"