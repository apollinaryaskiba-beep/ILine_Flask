import os
from flask import Flask, render_template, request, redirect, url_for, flash
from database import db, Employee
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from sqlalchemy.orm import aliased

app = Flask(__name__)
app.secret_key = "3131_secret_key"

# Подключение к PostgreSQL
DB_USER = "postgres"
DB_PASSWORD = "3131"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "postgres"

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Оптимизация пула для работы с 50 000 записей
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 20,
    "max_overflow": 40,
    "pool_timeout": 60,
    "pool_recycle": 1800,
}

db.init_app(app)

# Иерархия должностей
RANKS = ['ceo', 'manager', 'team lead', 'senior developer', 'developer']

def get_rank(position):
    pos = position.lower()
    for i, rank in enumerate(RANKS):
        if rank in pos:
            return i
    return 99 # Для всех остальных должностей

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

with app.app_context():
    db.create_all()
    print(f"Успех! База подключена. Сотрудников в системе: {Employee.query.count()}")

def is_circular(emp_id, new_mgr_id):
    # Рекурсивная проверка на циклическую зависимость
    if not new_mgr_id:
        return False
    curr_mgr = db.session.get(Employee, new_mgr_id)
    while curr_mgr:
        if curr_mgr.employee_id == int(emp_id):
            return True
        curr_mgr = curr_mgr.manager
    return False

@app.route("/")
@app.route("/")
def index():
    try:
        search_query = request.args.get('search', '').strip()
        sort_column = request.args.get('sort', 'full_name')
        direction = request.args.get('direction', 'asc')
        
        # Создаем псевдоним для таблицы начальников, чтобы по ним сортировать
        ManagerAlias = aliased(Employee)
        query = Employee.query.outerjoin(ManagerAlias, Employee.manager)

        if search_query:
            query = query.filter(Employee.full_name.ilike(f"%{search_query}%"))

        # Логика универсальной сортировки
        if sort_column == 'manager':
            # Сортировка по имени начальника
            col = ManagerAlias.full_name
        elif hasattr(Employee, sort_column):
            # Сортировка по остальным полям
            col = getattr(Employee, sort_column)
        else:
            col = Employee.full_name

        query = query.order_by(col.desc() if direction == 'desc' else col.asc())

        employees = query.limit(500).all()
        
        # Список для выпадающего меню (только руководители)
        all_staff = Employee.query.filter(
            or_(
                Employee.position.ilike('%ceo%'),
                Employee.position.ilike('%manager%'),
                Employee.position.ilike('%team lead%'),
                Employee.position.ilike('%senior developer%')
            )
        ).order_by(Employee.full_name).all()

        return render_template("index.html", 
                               employees=employees, 
                               all_staff=all_staff, 
                               search_query=search_query,
                               current_sort=sort_column,
                               current_dir=direction)
    except Exception as e:
        return f"Ошибка сервера: {e}", 500

@app.route("/update_manager", methods=["POST"])
def update_manager():
    try:
        emp_id = request.form.get("employee_id")
        mgr_id = request.form.get("manager_id")
        
        emp = db.session.get(Employee, emp_id)
        if not emp: return redirect(url_for('index'))

        # Если это не CEO, а ID начальника пустой — выдаем ошибку
        if not mgr_id and 'ceo' not in emp.position.lower():
            flash("Ошибка: У сотрудника обязательно должен быть руководитель!", "warning")
            return redirect(url_for('index'))

        if mgr_id:
            potential_boss = db.session.get(Employee, mgr_id)
            
            # Проверка
            if get_rank(potential_boss.position) > get_rank(emp.position):
                flash(f"Ошибка: {potential_boss.position} не может руководить {emp.position}!", "danger")
                return redirect(url_for('index'))

            # Проверка на цикличность
            if int(emp_id) == int(mgr_id) or is_circular(emp_id, mgr_id):
                flash("Ошибка: Недопустимая иерархия или циклическая зависимость!", "danger")
                return redirect(url_for('index'))

            # Сохраняем
            emp.manager_id = int(mgr_id)
            db.session.commit()
            flash(f"Руководитель для {emp.full_name} изменен", "success")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка: {str(e)}", "danger")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)