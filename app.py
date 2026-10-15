
from flask import Flask, request, redirect, url_for, render_template_string
from pymongo import MongoClient, ASCENDING
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError
from datetime import datetime
import os

app = Flask(__name__)

# 1. Connect Python to MongoDB
MONGO_URI = os.environ.get(
    "MONGO_URI", "mongodb://localhost:27017"
)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
client.admin.command("ping")

db = client["student_performance_db"]
students = db["students"]

# 2. Create indexes
students.create_index(
    [("roll_no", ASCENDING)], unique=True
)
students.create_index([
    ("department", ASCENDING),
    ("semester", ASCENDING)
])

# 3. Add demo data only if the collection is empty
if students.count_documents({}) == 0:
    demo_students = [
        {
            "name": "Aarav Sharma",
            "roll_no": "STU001",
            "department": "CSE",
            "semester": 5,
            "attendance": 82,
            "marks": {"dbms": 78, "python": 85, "nosql": 80}
        },
        {
            "name": "Priya Verma",
            "roll_no": "STU002",
            "department": "CSE",
            "semester": 5,
            "attendance": 91,
            "marks": {"dbms": 88, "python": 92, "nosql": 90}
        },
        {
            "name": "Rohan Kumar",
            "roll_no": "STU003",
            "department": "IT",
            "semester": 4,
            "attendance": 64,
            "marks": {"dbms": 55, "python": 61, "nosql": 58}
        },
        {
            "name": "Ananya Singh",
            "roll_no": "STU004",
            "department": "CSE",
            "semester": 5,
            "attendance": 76,
            "marks": {"dbms": 72, "python": 79, "nosql": 75}
        },
        {
            "name": "Kabir Gupta",
            "roll_no": "STU005",
            "department": "ECE",
            "semester": 3,
            "attendance": 88,
            "marks": {"dbms": 81, "python": 77, "nosql": 84}
        }
    ]
    students.insert_many(demo_students)


# 4. Calculate analytics using MongoDB aggregation
def get_analytics():
    pipeline = [
        {
            "$project": {
                "department": 1,
                "attendance": 1,
                "average": {
                    "$avg": [
                        "$marks.dbms",
                        "$marks.python",
                        "$marks.nosql"
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "average_marks": {"$avg": "$average"},
                "average_attendance": {"$avg": "$attendance"}
            }
        }
    ]

    result = list(students.aggregate(pipeline))
    if result:
        return result[0]

    return {
        "total": 0,
        "average_marks": 0,
        "average_attendance": 0
    }


# 5. Website dashboard
PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student Performance Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f6fb;
    color: #202b42;
}
header {
    background: #182541;
    color: white;
    padding: 23px 5%;
}
header h1 { margin: 0 0 7px; font-size: 25px; }
header p { margin: 0; color: #cbd5e7; }
main { max-width: 1200px; margin: auto; padding: 25px 4%; }
.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
}
.card, .panel {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 3px 14px #1725440d;
}
.card p { color: #65718a; margin: 0 0 12px; }
.card h2 { margin: 0; font-size: 28px; }
.charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 18px;
    margin-top: 22px;
}
.panel h3 { margin-top: 0; }
.form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
}
input, select, button {
    padding: 11px;
    border: 1px solid #d9dfeb;
    border-radius: 7px;
    font: inherit;
    min-width: 0;
}
button {
    background: #3157c8;
    color: white;
    border: none;
    cursor: pointer;
}
button:hover { background: #2343a2; }
.danger { background: #b83245; padding: 8px 10px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; }
th, td {
    text-align: left;
    padding: 12px 10px;
    border-bottom: 1px solid #edf0f5;
    white-space: nowrap;
}
th { color: #65718a; font-size: 13px; }
.note { color: #65718a; font-size: 13px; }
.message { color: #b83245; margin-bottom: 14px; }
@media(max-width: 600px) {
    main { padding: 16px 12px; }
    header { padding: 20px 16px; }
}
</style>
</head>
<body>
<header>
    <h1>Student Performance Analytics</h1>
    <p>Student records, academic performance and attendance insights</p>
</header>

<main>
    {% if message %}
      <p class="message">{{ message }}</p>
    {% endif %}

    <section class="cards">
        <div class="card">
            <p>Total Students</p>
            <h2>{{ total }}</h2>
        </div>
        <div class="card">
            <p>Average Marks</p>
            <h2>{{ avg_marks }} / 100</h2>
        </div>
        <div class="card">
            <p>Average Attendance</p>
            <h2>{{ avg_attendance }}%</h2>
        </div>
        <div class="card">
            <p>Students Below 75% Attendance</p>
            <h2>{{ low_attendance }}</h2>
        </div>
    </section>

    <section class="charts">
        <div class="panel">
            <h3>Subject-wise Average Marks</h3>
            <canvas id="marksChart"></canvas>
        </div>
        <div class="panel">
            <h3>Average Attendance by Department</h3>
            <canvas id="attendanceChart"></canvas>
        </div>
    </section>

    <section class="panel" style="margin-top:22px">
        <h3>Add a Student</h3>
        <form action="/add" method="post">
            <div class="form-grid">
                <input name="name" placeholder="Student name" required>
                <input name="roll_no" placeholder="Roll number" required>
                <input name="department" placeholder="Department (CSE)" required>
                <input name="semester" type="number" min="1" max="12"
                       placeholder="Semester" required>
                <input name="attendance" type="number" min="0" max="100"
                       placeholder="Attendance %" required>
                <input name="dbms" type="number" min="0" max="100"
                       placeholder="DBMS marks" required>
                <input name="python" type="number" min="0" max="100"
                       placeholder="Python marks" required>
                <input name="nosql" type="number" min="0" max="100"
                       placeholder="NoSQL marks" required>
                <button type="submit">Add Student</button>
            </div>
        </form>
    </section>

    <section class="panel" style="margin-top:22px">
        <h3>Student Records</h3>
        <form method="get" action="/" class="form-grid">
            <input name="q" value="{{ q }}"
                   placeholder="Search name or roll number">
            <button type="submit">Search</button>
            <a href="/" style="padding:11px">Clear search</a>
        </form>

        <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Name</th><th>Roll No.</th><th>Department</th>
                    <th>Semester</th><th>Attendance</th>
                    <th>DBMS</th><th>Python</th><th>NoSQL</th>
                    <th>Average</th><th>Action</th>
                </tr>
            </thead>
            <tbody>
            {% for s in records %}
                <tr>
                    <td>{{ s.name }}</td>
                    <td>{{ s.roll_no }}</td>
                    <td>{{ s.department }}</td>
                    <td>{{ s.semester }}</td>
                    <td>{{ s.attendance }}%</td>
                    <td>{{ s.marks.dbms }}</td>
                    <td>{{ s.marks.python }}</td>
                    <td>{{ s.marks.nosql }}</td>
                    <td>{{ "%.1f"|format(
                        (s.marks.dbms + s.marks.python + s.marks.nosql) / 3
                    ) }}</td>
                    <td>
                        <form action="/delete/{{ s._id }}" method="post"
                              onsubmit="return confirm('Delete this student?')">
                            <button class="danger" type="submit">Delete</button>
                        </form>
                    </td>
                </tr>
            {% else %}
                <tr><td colspan="10">No student records found.</td></tr>
            {% endfor %}
            </tbody>
        </table>
        </div>
        <p class="note">Data is fetched from MongoDB. Charts use live database results.</p>
    </section>
</main>

<script>
new Chart(document.getElementById("marksChart"), {
    type: "bar",
    data: {
        labels: ["DBMS", "Python", "NoSQL"],
        datasets: [{
            label: "Average marks",
            data: {{ subject_averages | tojson }},
            backgroundColor: ["#5274db", "#39a994", "#e9a44c"]
        }]
    },
    options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 100 } }
    }
});

new Chart(document.getElementById("attendanceChart"), {
    type: "bar",
    data: {
        labels: {{ dept_labels | tojson }},
        datasets: [{
            label: "Attendance %",
            data: {{ dept_values | tojson }},
            backgroundColor: "#5274db"
        }]
    },
    options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 100 } }
    }
});
</script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    q = request.args.get("q", "").strip()

    query = {}
    if q:
        query = {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"roll_no": {"$regex": q, "$options": "i"}}
            ]
        }

    records = list(students.find(query).sort("roll_no", ASCENDING))
    stats = get_analytics()

    low_attendance = students.count_documents({"attendance": {"$lt": 75}})

    subject_pipeline = [
        {
            "$group": {
                "_id": None,
                "dbms": {"$avg": "$marks.dbms"},
                "python": {"$avg": "$marks.python"},
                "nosql": {"$avg": "$marks.nosql"}
            }
        }
    ]
    subject_result = list(students.aggregate(subject_pipeline))
    subject_averages = [0, 0, 0]
    if subject_result:
        row = subject_result[0]
        subject_averages = [
            round(row.get("dbms") or 0, 2),
            round(row.get("python") or 0, 2),
            round(row.get("nosql") or 0, 2)
        ]

    dept_pipeline = [
        {
            "$group": {
                "_id": "$department",
                "avg_attendance": {"$avg": "$attendance"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    dept_result = list(students.aggregate(dept_pipeline))

    message = request.args.get("message", "")

    return render_template_string(
        PAGE,
        records=records,
        total=stats.get("total", 0),
        avg_marks=round(stats.get("average_marks") or 0, 1),
        avg_attendance=round(stats.get("average_attendance") or 0, 1),
        low_attendance=low_attendance,
        subject_averages=subject_averages,
        dept_labels=[r["_id"] for r in dept_result],
        dept_values=[round(r["avg_attendance"], 1) for r in dept_result],
        q=q,
        message=message
    )


@app.route("/add", methods=["POST"])
def add_student():
    try:
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip().upper()
        department = request.form.get("department", "").strip().upper()
        semester = int(request.form["semester"])
        attendance = int(request.form["attendance"])
        dbms = int(request.form["dbms"])
        python_marks = int(request.form["python"])
        nosql = int(request.form["nosql"])

        if not name or not roll_no or not department:
            raise ValueError("Name, roll number and department are required.")

        if not 1 <= semester <= 12:
            raise ValueError("Semester must be between 1 and 12.")

        if not 0 <= attendance <= 100:
            raise ValueError("Attendance must be between 0 and 100.")

        if not all(0 <= mark <= 100 for mark in
                   [dbms, python_marks, nosql]):
            raise ValueError("All marks must be between 0 and 100.")

        students.insert_one({
            "name": name,
            "roll_no": roll_no,
            "department": department,
            "semester": semester,
            "attendance": attendance,
            "marks": {
                "dbms": dbms,
                "python": python_marks,
                "nosql": nosql
            }
        })

        return redirect(url_for("dashboard",
                                message="Student added successfully!"))

    except DuplicateKeyError:
        return redirect(url_for("dashboard",
                                message="That roll number already exists."))

    except (ValueError, KeyError):
        return redirect(url_for("dashboard",
                                message="Invalid input. Check all fields and ranges."))


@app.route("/delete/<student_id>", methods=["POST"])
def delete_student(student_id):
    try:
        students.delete_one({"_id": ObjectId(student_id)})
        return redirect(url_for("dashboard",
                                message="Student deleted successfully."))
    except Exception:
        return redirect(url_for("dashboard",
                                message="Could not delete that student."))


if __name__ == "__main__":
    print("MongoDB connected. Starting Student Performance Dashboard...")
    app.run(debug=True)
