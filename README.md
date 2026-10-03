To add this to your project, create a new file in the exact same folder as your `app.py` script, name it `README.md`, and paste the following content into it:

```markdown
# Dynamic Timetable Generator

> A smart, automated scheduling platform designed to eliminate the complexities of academic planning and personal study management.

The **Dynamic Timetable Generator** utilizes an advanced heuristic constraint-solving algorithm to instantly resolve complex scheduling conflicts, ensuring zero overlaps for teachers, students, or room capacities. Built on a robust Flask and SQLAlchemy backend, it features a highly responsive, modern Glassmorphism UI engineered with Tailwind CSS. Users can seamlessly manage institutional data in real-time, monitor live optimization metrics, and instantly export generated schedules for a frictionless administrative experience.

## ✨ Key Features

*   **Smart Heuristic Scheduling Engine:** Intelligently processes complex constraints including room capacities, specific room-type requirements (Labs, Auditoriums, Classrooms), and teacher daily workload limits.
*   **Conflict Resolution Protocol:** Automatically tracks and reports unresolvable bottlenecks (e.g., a class size exceeding the largest available room) without crashing the schedule generation.
*   **Dual Operating Modes:**
    *   **Institutional/Admin Mode:** Manage comprehensive university-level data including Rooms, Teachers, Courses, and Student Enrollments.
    *   **Student Mode:** A dedicated personal study planner that converts the engine into an automated task manager, distributing subjects across available free timeslots.
*   **Live Optimization Dashboard:** Real-time calculation of total classes scheduled, overall room utilization percentages, and remaining empty slots.
*   **One-Click Exports:** Instant client-side generation for beautifully formatted landscape PDFs (via `html2pdf.js`) and Excel/CSV formats.
*   **Glassmorphism UI:** A sleek, animated, and fully responsive dark-mode interface built entirely with Tailwind CSS and Vanilla JavaScript.

## 🛠 Tech Stack

*   **Backend:** Python 3, Flask, SQLAlchemy
*   **Database:** SQLite
*   **Frontend:** HTML5, CSS3, Tailwind CSS (via CDN), Vanilla JavaScript, FontAwesome
*   **Export Libraries:** `html2pdf.js`

## 🚀 Installation & Setup

1. **Clone or Download the Repository**
   Ensure you have Python 3.x installed on your machine.

2. **Install Dependencies**
   Open your terminal and install the required Python packages:
   ```bash
   pip install Flask Flask-SQLAlchemy

```

3. **Run the Application**
Navigate to the project directory and run the main application file:
```bash
python app.py

```


4. **Access the Web Interface**
Once the server starts, open your web browser and navigate to:
```text
[http://127.0.0.1:5001](http://127.0.0.1:5001)

```



## 📖 Usage Guide

### Getting Started

Upon launching the application, you will be greeted by the landing screen offering three modes:

* **Template Mode:** Instantly loads pre-configured institutional dummy data (Rooms, Teachers, Courses) so you can immediately test the scheduling engine.
* **Custom Build:** Starts you with a completely blank database to build your institution's parameters from scratch.
* **Student Mode:** Transforms the application into a personal planner, hiding institutional complexities and allowing you to solely input study timeslots and subjects.

### Generating a Schedule

1. Enter your operational parameters into the Data Editor panels (Timeslots, Rooms, Teachers, Courses).
2. Click **Generate Plan** in the top right corner.
3. The engine will optimize the schedule and automatically scroll down to reveal the timetable and utilization metrics.

### Understanding Conflicts

If a strict physical constraint is broken—such as assigning a 90-person class to a Lab when the largest available lab only holds 80—the engine will schedule all valid classes and issue a **Partial Schedule Warning**. This allows administrators to quickly identify the bottleneck, edit the specific room or course capacity, and regenerate the plan.



```

```
