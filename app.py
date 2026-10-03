import os
import random
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==========================================
# 1. ENHANCED DATABASE MODELS
# ==========================================
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), default="Classroom")

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    max_hours_per_day = db.Column(db.Integer, default=4)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    enrolled_count = db.Column(db.Integer, nullable=False)
    weekly_hours = db.Column(db.Integer, default=1)
    room_type = db.Column(db.String(50), default="Classroom")
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=True)

class Timeslot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class StudentEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# ==========================================
# 2. FRONTEND HTML & CSS TEMPLATE
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dynamic Timetable Generator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        body {
            background-color: #050b14;
            background-image: 
                radial-gradient(circle at 15% 35%, rgba(99, 102, 241, 0.25) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(217, 70, 239, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 50% 10%, rgba(14, 165, 233, 0.1) 0%, transparent 50%),
                linear-gradient(to bottom right, #050b14, #0f172a);
            background-attachment: fixed;
            background-size: cover;
            overflow-x: hidden;
        }

        .orb {
            position: fixed;
            border-radius: 50%;
            filter: blur(90px);
            z-index: -2;
            transition: transform 6s ease-in-out; 
        }
        .orb-1 { top: 5%; left: 10%; width: 400px; height: 400px; background: rgba(99, 102, 241, 0.25); }
        .orb-2 { bottom: 10%; right: 5%; width: 500px; height: 500px; background: rgba(217, 70, 239, 0.15); }
        .orb-3 { top: 40%; left: 40%; width: 350px; height: 350px; background: rgba(14, 165, 233, 0.15); }

        #cursor-glow {
            position: fixed;
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: conic-gradient(from 0deg, #ff0000, #ff7f00, #ffff00, #00ff00, #00ffff, #0000ff, #8b00ff, #ff0000);
            filter: blur(40px);
            opacity: 0.4;
            pointer-events: none; 
            z-index: -1; 
            transform: translate(-50%, -50%);
            transition: top 0.15s ease-out, left 0.15s ease-out; 
        }
        
        .force-show-actions .opacity-0 { opacity: 1 !important; }
        #page-loader { transition: opacity 0.6s ease-out, visibility 0.6s ease-out; }
        .loader-hidden { opacity: 0; visibility: hidden; pointer-events: none; }
        
        h1, h2, h3, p, label { transition: transform 0.3s ease, color 0.3s ease; display: inline-block; width: 100%; }
        h1:hover, h2:hover, h3:hover, p:hover, label:hover { transform: translateY(-3px); color: #818cf8; }
        th, td { transition: color 0.3s ease; }
        th:hover, td:hover { color: #818cf8; }
        button, a, input, select { display: inline-block; width: auto; }
        form input, form select { width: 100%; }
        
        .pdf-mode .hide-on-export { display: none !important; }
        .pdf-solid-bg { background-color: #0f172a !important; backdrop-filter: none !important; }
        input[type=range] { accent-color: #6366f1; width: 100%; }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(30, 41, 59, 0.5); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(99, 102, 241, 0.5); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.8); }

        @keyframes slideInRight { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes fadeOutDown { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(20px); } }
        .toast-enter { animation: slideInRight 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
        .toast-leave { animation: fadeOutDown 0.3s ease-in forwards; }
    </style>
</head>
<body class="text-slate-200 font-sans min-h-screen p-8 flex flex-col justify-between" onload="initPage()">

    <div id="cursor-glow"></div>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <div id="toast-container" class="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none"></div>

    <div id="page-loader" class="fixed inset-0 z-50 bg-slate-900/90 backdrop-blur-md flex flex-col items-center justify-center">
        <i class="fas fa-hourglass-half fa-spin text-6xl text-indigo-400 mb-6"></i>
        <h2 class="text-2xl font-extrabold text-white tracking-widest animate-pulse" style="width: auto;">CALCULATING TIMETABLE...</h2>
    </div>

    <div class="flex-grow">
        <div id="landing-screen" class="max-w-6xl mx-auto mt-16 flex flex-col items-center">
            <h1 class="text-5xl font-extrabold text-white tracking-tight mb-3 drop-shadow-lg" style="width: auto;"><i class="fas fa-calendar-alt mr-3 text-indigo-400"></i>Timetable Generator</h1>
            <p class="text-slate-300 mb-6 text-lg drop-shadow" style="width: auto;">3 Modes to Choose, Add your details below and see your schedule come together.</p>
            
            <div class="mb-10 max-w-xl text-center px-6 py-3 rounded-xl bg-slate-900/40 border border-slate-700/40 backdrop-blur-sm shadow-inner transition-opacity duration-500" id="quote-container">
                <p id="quote-text" class="text-indigo-200/90 text-sm italic font-medium tracking-wide leading-relaxed">"Loading..."</p>
                <span id="quote-author" class="block text-slate-400 text-xs mt-1 font-semibold tracking-wider uppercase">— Author</span>
            </div>
            
            <div class="grid md:grid-cols-3 gap-8 w-full">
                <!-- Institutional Template -->
                <div onclick="startWithTemplate()" class="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-8 text-center transition hover:shadow-indigo-500/20 hover:-translate-y-1 cursor-pointer">
                    <div class="w-16 h-16 mx-auto bg-indigo-500/20 rounded-full flex items-center justify-center mb-4 border border-indigo-500/30">
                        <i class="fas fa-magic text-2xl text-indigo-400"></i>
                    </div>
                    <h2 class="text-xl font-bold text-white mb-2">Template Mode</h2>
                    <p class="text-slate-400 mb-6 text-sm">Start with pre-filled institutional dummy data that you can edit and preview immediately.</p>
                    <button class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-lg">Load Template</button>
                </div>
                <!-- Blank Custom -->
                <div onclick="startCustom()" class="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-8 text-center transition hover:shadow-emerald-500/20 hover:-translate-y-1 cursor-pointer">
                    <div class="w-16 h-16 mx-auto bg-emerald-500/20 rounded-full flex items-center justify-center mb-4 border border-emerald-500/30">
                        <i class="fas fa-plus text-2xl text-emerald-400"></i>
                    </div>
                    <h2 class="text-xl font-bold text-white mb-2">Custom Build</h2>
                    <p class="text-slate-400 mb-6 text-sm">Start with a completely blank canvas. Add rooms, teachers, and courses from scratch.</p>
                    <button class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-lg">Create Custom</button>
                </div>
                <!-- NEW: Student Mode -->
                <div onclick="startStudentMode()" class="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-8 text-center transition hover:shadow-cyan-500/20 hover:-translate-y-1 cursor-pointer">
                    <div class="w-16 h-16 mx-auto bg-cyan-500/20 rounded-full flex items-center justify-center mb-4 border border-cyan-500/30">
                        <i class="fas fa-user-graduate text-2xl text-cyan-400"></i>
                    </div>
                    <h2 class="text-xl font-bold text-white mb-2">Student Mode</h2>
                    <p class="text-slate-400 mb-6 text-sm">Personal study planner. Define your free times and subjects, and let the app build your schedule.</p>
                    <button class="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-lg">Start Planning</button>
                </div>
            </div>
        </div>

        <div id="main-dashboard" class="max-w-7xl mx-auto hidden">
            <header class="flex justify-between items-center mb-8 bg-slate-900/60 backdrop-blur-md p-6 rounded-2xl border border-slate-700/50 shadow-2xl">
                <div class="flex items-center gap-5">
                    <button onclick="backToHome()" class="bg-slate-800 border border-slate-600 hover:bg-slate-700 text-slate-300 rounded-full w-12 h-12 flex items-center justify-center transition shadow-lg"><i class="fas fa-arrow-left"></i></button>
                    <div>
                        <h1 class="text-3xl font-extrabold text-white tracking-tight drop-shadow-md" style="width: auto;"><i class="fas fa-edit mr-3 text-indigo-400"></i>Data Editor</h1>
                        <p class="text-slate-400 text-sm mt-1">Configure your constraints below and preview the optimized schedule.</p>
                    </div>
                </div>
                <div class="flex gap-3">
                    <button onclick="startWithTemplate()" class="bg-indigo-500/20 hover:bg-indigo-500/40 border border-indigo-500/30 text-indigo-300 font-semibold py-2 px-4 rounded-lg transition-colors shadow-lg text-sm hide-in-student"><i class="fas fa-undo mr-1"></i> Reset Template</button>
                    <button onclick="resetData()" class="bg-rose-500/20 hover:bg-rose-500/40 border border-rose-500/30 text-rose-300 font-semibold py-2 px-4 rounded-lg transition-colors shadow-lg text-sm"><i class="fas fa-trash-alt mr-1"></i> Clear Data</button>
                    <button onclick="previewSchedule(this)" class="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2 px-6 rounded-lg transition-colors shadow-lg"><i class="fas fa-eye mr-1"></i> Generate Plan</button>
                </div>
            </header>

            <div id="dashboard-grid" class="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8 transition-all">
                
                <!-- Timeslots -->
                <div id="panel-timeslots" class="bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-5">
                    <h3 class="font-bold text-slate-200 mb-3 border-b border-slate-700 pb-2" style="width:auto;"><i class="far fa-clock mr-2 text-indigo-400"></i>Timeslots</h3>
                    <div class="space-y-3 mb-4">
                        <div>
                            <label class="text-xs font-semibold text-slate-500 block mb-1">Day</label>
                            <div id="day-selector" class="flex flex-wrap gap-1">
                                <button type="button" onclick="selectDay('Mon')" class="day-btn px-2 py-1 text-xs font-bold rounded bg-indigo-500 text-white transition">Mon</button>
                                <button type="button" onclick="selectDay('Tue')" class="day-btn px-2 py-1 text-xs font-bold rounded bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700 transition">Tue</button>
                                <button type="button" onclick="selectDay('Wed')" class="day-btn px-2 py-1 text-xs font-bold rounded bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700 transition">Wed</button>
                                <button type="button" onclick="selectDay('Thu')" class="day-btn px-2 py-1 text-xs font-bold rounded bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700 transition">Thu</button>
                                <button type="button" onclick="selectDay('Fri')" class="day-btn px-2 py-1 text-xs font-bold rounded bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700 transition">Fri</button>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <div class="flex-1">
                                <label class="text-xs font-semibold text-slate-500 block mb-1">Start Time</label>
                                <input type="time" id="time-start" value="09:00" class="w-full p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white focus:ring focus:ring-indigo-500 transition" style="color-scheme: dark;" onchange="updateTimePreview()" required>
                            </div>
                            <div class="flex-1">
                                <label class="text-xs font-semibold text-slate-500 block mb-1">End Time</label>
                                <input type="time" id="time-end" value="10:00" class="w-full p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white focus:ring focus:ring-indigo-500 transition" style="color-scheme: dark;" onchange="updateTimePreview()" required>
                            </div>
                        </div>
                        <div class="pt-3 border-t border-slate-700">
                            <div class="text-xs text-slate-400 mb-2">Preview: <strong id="time-preview" class="text-white">Mon 09:00 AM - 10:00 AM</strong></div>
                            <button type="button" id="btn-timeslot-submit" onclick="submitTimeslot()" class="w-full bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/40 text-indigo-300 py-1.5 rounded text-sm font-semibold transition">Add Timeslot</button>
                            <button type="button" onclick="document.getElementById('list-timeslots').classList.toggle('force-show-actions')" class="w-full mt-2 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 text-slate-400 py-1 rounded text-xs font-semibold transition"><i class="fas fa-edit"></i> Edit</button>
                        </div>
                    </div>
                    <ul id="list-timeslots" class="text-sm text-slate-300 space-y-1 h-32 overflow-y-auto border-t border-slate-700 pt-2"></ul>
                </div>

                <!-- Rooms -->
                <div id="panel-rooms" class="bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-5">
                    <h3 class="font-bold text-slate-200 mb-3 border-b border-slate-700 pb-2" style="width:auto;"><i class="fas fa-door-open mr-2 text-indigo-400"></i>Rooms</h3>
                    <form onsubmit="addData(event, '/api/room', 'room')" class="mb-4">
                        <input type="text" id="rm-name" placeholder="Room Name (e.g. Hall A)" class="w-full mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                        <div class="flex gap-2 mb-2">
                            <div class="flex-1">
                                <label class="text-xs font-semibold text-slate-500 block mb-1">Capacity</label>
                                <input type="number" id="rm-cap" min="0" placeholder="e.g. 50" class="w-full p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                            </div>
                            <div class="flex-1">
                                <label class="text-xs font-semibold text-slate-500 block mb-1">Room Type</label>
                                <select id="rm-type" class="w-full p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white focus:ring focus:ring-indigo-500 transition" required>
                                    <option value="Classroom">Classroom</option>
                                    <option value="Lab">Lab</option>
                                    <option value="Auditorium">Auditorium</option>
                                </select>
                            </div>
                        </div>
                        <button type="submit" class="w-full bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/40 text-indigo-300 py-1.5 rounded text-sm font-semibold transition">Add Room</button>
                        <button type="button" onclick="document.getElementById('list-rooms').classList.toggle('force-show-actions')" class="w-full mt-2 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 text-slate-400 py-1 rounded text-xs font-semibold transition"><i class="fas fa-edit"></i> Edit</button>
                    </form>
                    <ul id="list-rooms" class="text-sm text-slate-300 space-y-1 h-80 overflow-y-auto"></ul>
                </div>

                <!-- Teachers -->
                <div id="panel-teachers" class="bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-5">
                    <h3 class="font-bold text-slate-200 mb-3 border-b border-slate-700 pb-2" style="width:auto;"><i class="fas fa-chalkboard-teacher mr-2 text-indigo-400"></i>Teachers</h3>
                    <form onsubmit="addData(event, '/api/teacher', 'teacher')" class="mb-4">
                        <input type="text" id="tc-name" placeholder="Teacher Name (e.g. Dr. Smith)" class="w-full mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                        <div>
                            <label class="text-xs font-semibold text-slate-500 block mb-1">Max Classes per Day</label>
                            <input type="number" id="tc-max" min="1" max="15" value="4" class="w-full mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                        </div>
                        <button type="submit" class="w-full bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/40 text-indigo-300 py-1.5 rounded text-sm font-semibold transition">Add Teacher</button>
                        <button type="button" onclick="document.getElementById('list-teachers').classList.toggle('force-show-actions')" class="w-full mt-2 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 text-slate-400 py-1 rounded text-xs font-semibold transition"><i class="fas fa-edit"></i> Edit</button>
                    </form>
                    <ul id="list-teachers" class="text-sm text-slate-300 space-y-1 h-80 overflow-y-auto"></ul>
                </div>

                <!-- Courses -->
                <div id="panel-courses" class="bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-5">
                    <h3 id="course-panel-title" class="font-bold text-slate-200 mb-3 border-b border-slate-700 pb-2" style="width:auto;"><i class="fas fa-book mr-2 text-indigo-400"></i>Courses</h3>
                    <form onsubmit="addData(event, '/api/course', 'course')" class="mb-4">
                        <input type="text" id="cr-code" placeholder="Course Code (e.g. CS101)" class="w-full mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                        <div class="flex gap-2 mb-2">
                            <div class="flex-1" id="wrap-enroll">
                                <label class="text-xs font-semibold text-slate-500 block mb-1">Class Size</label>
                                <input type="number" id="cr-enroll" min="0" placeholder="e.g. 60" class="w-full p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                            </div>
                            <div class="flex-1">
                                <label class="text-xs font-semibold text-slate-500 block mb-1">Hours / Week</label>
                                <input type="number" id="cr-hours" min="1" max="10" value="1" class="w-full p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                            </div>
                        </div>
                        <select id="cr-type" class="w-full mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white focus:ring focus:ring-indigo-500 transition" required>
                            <option value="Classroom">Requires Classroom</option>
                            <option value="Lab">Requires Lab</option>
                            <option value="Auditorium">Requires Auditorium</option>
                        </select>
                        <select id="cr-teacher" class="w-full mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white focus:ring focus:ring-indigo-500 transition">
                            <option value="">Assign Teacher (Optional)</option>
                        </select>
                        <button type="submit" id="btn-course-submit" class="w-full bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/40 text-indigo-300 py-1.5 rounded text-sm font-semibold transition">Add Timeslot</button>
                        <button type="button" onclick="document.getElementById('list-courses').classList.toggle('force-show-actions')" class="w-full mt-2 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 text-slate-400 py-1 rounded text-xs font-semibold transition"><i class="fas fa-edit"></i> Edit</button>
                    </form>
                    <ul id="list-courses" class="text-sm text-slate-300 space-y-1 h-64 overflow-y-auto"></ul>
                </div>

                <!-- Enrollments -->
                <div id="panel-enrollments" class="bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-5">
                    <h3 class="font-bold text-slate-200 mb-3 border-b border-slate-700 pb-2" style="width:auto;"><i class="fas fa-user-graduate mr-2 text-indigo-400"></i>Enrollments</h3>
                    <form onsubmit="addData(event, '/api/enrollment', 'enrollment')" class="mb-4">
                        <input type="text" id="en-student" placeholder="Student ID (e.g. S-01)" class="mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white placeholder-slate-500 focus:ring focus:ring-indigo-500 transition" required>
                        <select id="en-course" class="mb-2 p-2 bg-slate-800/80 border border-slate-600 rounded text-sm text-white focus:ring focus:ring-indigo-500 transition" required>
                            <option value="">Select Course...</option>
                        </select>
                        <button type="submit" class="w-full bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/40 text-indigo-300 py-1.5 rounded text-sm font-semibold transition">Add Enrollment</button>
                        <button type="button" onclick="document.getElementById('list-enrollments').classList.toggle('force-show-actions')" class="w-full mt-2 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 text-slate-400 py-1 rounded text-xs font-semibold transition"><i class="fas fa-edit"></i> Edit</button>
                    </form>
                    <ul id="list-enrollments" class="text-sm text-slate-300 space-y-1 h-80 overflow-y-auto"></ul>
                </div>
            </div>

            <div id="results-container" class="bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden hidden transition-all">
                
                <!-- Optimization Metrics Dashboard -->
                <div id="metrics-dashboard" class="grid grid-cols-3 divide-x divide-slate-700/50 border-b border-slate-700 bg-slate-800/30 text-center py-4 hide-in-student">
                    <div>
                        <p class="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Total Classes Scheduled</p>
                        <h4 id="metric-classes" class="text-2xl font-extrabold text-indigo-400">0</h4>
                    </div>
                    <div>
                        <p class="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Room Utilization</p>
                        <h4 id="metric-utilization" class="text-2xl font-extrabold text-emerald-400">0%</h4>
                    </div>
                    <div>
                        <p class="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Empty Slots</p>
                        <h4 id="metric-empty" class="text-2xl font-extrabold text-amber-400">0</h4>
                    </div>
                </div>

                <div class="bg-slate-800/80 border-b border-slate-700 px-6 py-4 flex justify-between items-center hide-on-export">
                    <h2 class="text-lg font-bold text-white" style="width: auto;"><i class="fas fa-calendar-check text-emerald-400 mr-2"></i>Schedule Preview</h2>
                    <div class="flex gap-3">
                        <button id="export-csv-btn" onclick="exportCSV()" class="bg-emerald-600 hover:bg-emerald-500 text-white py-1.5 px-4 rounded text-sm font-semibold transition shadow-lg">
                            <i class="fas fa-file-excel mr-1"></i> Excel / CSV
                        </button>
                        <button id="export-btn" onclick="exportPDF()" class="bg-indigo-600 hover:bg-indigo-500 text-white py-1.5 px-4 rounded text-sm font-semibold transition shadow-lg">
                            <i class="fas fa-file-pdf mr-1"></i> Export PDF
                        </button>
                    </div>
                </div>
                <div class="overflow-x-auto p-4" id="pdf-wrapper">
                    <table id="schedule-table" class="w-full text-left border-collapse">
                        <thead>
                            <tr id="schedule-header" class="text-slate-400 text-sm uppercase tracking-wider border-b border-slate-700">
                                <th class="px-6 py-4 font-semibold">Timeslot</th>
                                <th class="px-6 py-4 font-semibold">Course</th>
                                <th class="px-6 py-4 font-semibold">Teacher</th>
                                <th class="px-6 py-4 font-semibold">Room</th>
                                <th class="px-6 py-4 font-semibold">Students</th>
                            </tr>
                        </thead>
                        <tbody id="schedule-body" class="divide-y divide-slate-700/50"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Contact Info Footer -->
    <footer class="max-w-7xl mx-auto w-full mt-12 bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl p-6">
        <div class="flex flex-col md:flex-row justify-between items-center md:items-start gap-6">
            <div class="text-center md:text-left">
                <h3 class="text-xl font-bold text-white mb-1"><i class="fas fa-building text-indigo-400 mr-2"></i>Data Alcott Systems</h3>
                <p class="text-sm text-slate-400 uppercase tracking-widest font-semibold">Contact Us</p>
                <button onclick="openAbout()" class="mt-3 text-xs bg-indigo-500/20 hover:bg-indigo-500/40 border border-indigo-500/30 text-indigo-300 font-semibold py-1.5 px-4 rounded-lg transition-colors shadow-lg">
                    <i class="fas fa-info-circle mr-1"></i> About App
                </button>
            </div>
            <div class="flex flex-wrap justify-center md:justify-end gap-x-6 gap-y-3 text-sm text-slate-300">
                <div class="flex items-center hover:text-white transition"><i class="fas fa-phone-alt text-emerald-400 mr-2"></i>+91 9600095045</div>
                <div class="flex items-center hover:text-white transition"><i class="fas fa-envelope text-indigo-400 mr-2"></i>mail@freeinternships.in</div>
                <div class="flex items-center hover:text-white transition"><i class="fas fa-globe text-blue-400 mr-2"></i>www.freeinternships.in</div>
                <div class="flex items-center hover:text-white transition"><i class="fas fa-map-marker-alt text-rose-400 mr-2"></i>Chennai</div>
                <div class="flex items-center hover:text-white transition"><i class="fas fa-clock text-amber-400 mr-2"></i>Mon - Sat: 11:00 AM - 5:00 PM</div>
            </div>
        </div>
    </footer>

    <!-- About Modal -->
    <div id="about-modal" class="fixed inset-0 z-[110] bg-slate-900/80 backdrop-blur-md flex items-center justify-center hidden opacity-0 transition-opacity duration-300">
        <div id="about-modal-content" class="bg-slate-800/90 border border-slate-600 p-8 rounded-2xl shadow-2xl max-w-2xl mx-4 relative transform scale-95 transition-transform duration-300">
            <button onclick="closeAbout()" class="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full bg-slate-700 text-slate-400 hover:bg-rose-500 hover:text-white transition-colors">
                <i class="fas fa-times"></i>
            </button>
            <h2 class="text-2xl font-bold text-white mb-4"><i class="fas fa-info-circle text-indigo-400 mr-2"></i>About the Application</h2>
            <p class="text-slate-300 leading-relaxed text-sm text-justify">
                The Dynamic Timetable Generator is a smart, automated scheduling platform designed to eliminate the complexities of academic planning. Powered by an advanced heuristic solver, the application instantly resolves complex scheduling constraints, tracking unresolvable conflicts without crashing. Built on a robust Flask and SQLAlchemy backend, it features a highly responsive, modern Glassmorphism UI engineered with Tailwind CSS. Users can seamlessly manage institutional data—including distinct room types and teacher capacity—in real-time, monitor live optimization metrics, and instantly export generated schedules to PDF or CSV formats for a frictionless administrative experience.
            </p>
        </div>
    </div>

    <script>
        const timeQuotes = [
            { text: "Time is what we want most, but what we use worst.", author: "William Penn" },
            { text: "The secret of getting ahead is getting started.", author: "Mark Twain" },
            { text: "You may delay, but time will not.", author: "Benjamin Franklin" },
            { text: "The two most powerful warriors are patience and time.", author: "Leo Tolstoy" },
            { text: "Don't watch the clock; do what it does. Keep going.", author: "Sam Levenson" },
            { text: "The bad news is time flies. The good news is you're the pilot.", author: "Michael Altshuler" },
            { text: "A year from now you may wish you had started today.", author: "Karen Lamb" },
            { text: "Time is more value than money. You can get more money, but you cannot get more time.", author: "Jim Rohn" },
            { text: "Yesterday is gone. Tomorrow has not yet come. We have only today. Let us begin.", author: "Mother Teresa" },
            { text: "Time is a created thing. To say 'I don't have time,' is like saying, 'I don't want to.'", author: "Lao Tzu" }
        ];

        function displayRandomQuote() {
            const randomIdx = Math.floor(Math.random() * timeQuotes.length);
            const quote = timeQuotes[randomIdx];
            document.getElementById('quote-text').innerText = `"${quote.text}"`;
            document.getElementById('quote-author').innerText = `— ${quote.author}`;
        }

        document.addEventListener('mousemove', (e) => {
            const glow = document.getElementById('cursor-glow');
            glow.style.left = e.clientX + 'px';
            glow.style.top = e.clientY + 'px';
        });

        function moveOrbsRandomly() {
            document.querySelectorAll('.orb').forEach(orb => {
                const randomX = Math.floor(Math.random() * 800) - 400;
                const randomY = Math.floor(Math.random() * 800) - 400;
                const randomScale = (Math.random() * 0.4) + 0.8; 
                orb.style.transform = `translate(${randomX}px, ${randomY}px) scale(${randomScale})`;
            });
        }
        setTimeout(moveOrbsRandomly, 100);
        setInterval(moveOrbsRandomly, 6000); 

        let selectedDay = 'Mon';
        let currentMode = 'admin'; 
        let appData = { rooms: [], courses: [], enrollments: [], timeslots: [], teachers: [] };
        let editState = { room: null, course: null, enrollment: null, timeslot: null, teacher: null };

        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            const bgColor = type === 'error' ? 'bg-rose-500' : 'bg-emerald-500';
            const icon = type === 'error' ? 'fa-exclamation-circle' : 'fa-check-circle';
            toast.className = `flex items-center gap-3 text-white px-5 py-3 rounded-lg shadow-xl pointer-events-auto ${bgColor} toast-enter border border-white/20`;
            toast.innerHTML = `<i class="fas ${icon} text-lg"></i><span class="text-sm font-medium leading-tight max-w-xs">${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.classList.remove('toast-enter');
                toast.classList.add('toast-leave');
                setTimeout(() => toast.remove(), 300);
            }, 4000); 
        }
        function formatTime(time24) {
            if(!time24) return "";
            let [h, m] = time24.split(':');
            let hours = parseInt(h);
            let ampm = hours >= 12 ? 'PM' : 'AM';
            hours = hours % 12;
            hours = hours ? hours : 12;
            return `${hours.toString().padStart(2, '0')}:${m} ${ampm}`;
        }

        function parseTime(time12, ampm) {
            let [h, m] = time12.split(':');
            h = parseInt(h);
            if(ampm === 'PM' && h !== 12) h += 12;
            if(ampm === 'AM' && h === 12) h = 0;
            return `${h.toString().padStart(2, '0')}:${m}`;
        }

        function updateTimePreview() {
            const start = document.getElementById('time-start').value;
            const end = document.getElementById('time-end').value;
            if (start && end) {
                document.getElementById('time-preview').innerText = `${selectedDay} ${formatTime(start)} - ${formatTime(end)}`;
            }
        }
        
        function initPage() {
            displayRandomQuote();
            updateTimePreview();
            setTimeout(() => { document.getElementById('page-loader').classList.add('loader-hidden'); }, 800);
        }

        function openAbout() {
            const modal = document.getElementById('about-modal');
            const content = document.getElementById('about-modal-content');
            modal.classList.remove('hidden');
            setTimeout(() => {
                modal.classList.remove('opacity-0');
                content.classList.remove('scale-95');
                content.classList.add('scale-100');
            }, 10);
        }

        function closeAbout() {
            const modal = document.getElementById('about-modal');
            const content = document.getElementById('about-modal-content');
            modal.classList.add('opacity-0');
            content.classList.remove('scale-100');
            content.classList.add('scale-95');
            setTimeout(() => {
                modal.classList.add('hidden');
            }, 300);
        }

        function resetUIForAdmin() {
            currentMode = 'admin';
            document.getElementById('panel-rooms').classList.remove('hidden');
            document.getElementById('panel-teachers').classList.remove('hidden');
            document.getElementById('panel-enrollments').classList.remove('hidden');
            document.getElementById('course-panel-title').innerHTML = '<i class="fas fa-book mr-2 text-indigo-400"></i>Courses';
            document.getElementById('cr-code').placeholder = "Course Code (e.g. CS101)";
            document.getElementById('wrap-enroll').classList.remove('hidden');
            document.getElementById('cr-type').classList.remove('hidden');
            document.getElementById('cr-teacher').classList.remove('hidden');
            document.getElementById('btn-course-submit').innerHTML = "Add Course";
            document.getElementById('dashboard-grid').className = "grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8 transition-all";
            
            document.querySelectorAll('.hide-in-student').forEach(el => el.classList.remove('hidden'));
        }

        async function startWithTemplate() {
            document.getElementById('page-loader').classList.remove('loader-hidden');
            resetUIForAdmin();
            try {
                await fetch('/api/setup_dummy', { method: 'POST' });
                await fetchData();
                showToast('Template data loaded successfully!', 'success');
                switchToDashboard();
            } catch (err) { showToast('Network error.', 'error'); document.getElementById('page-loader').classList.add('loader-hidden'); }
        }

        async function startCustom() {
            document.getElementById('page-loader').classList.remove('loader-hidden');
            resetUIForAdmin();
            try {
                await fetch('/api/reset', { method: 'POST' });
                await fetchData();
                switchToDashboard();
            } catch (err) { showToast('Network error.', 'error'); document.getElementById('page-loader').classList.add('loader-hidden'); }
        }

        async function startStudentMode() {
            document.getElementById('page-loader').classList.remove('loader-hidden');
            currentMode = 'student';
            try {
                await fetch('/api/setup_student', { method: 'POST' });
                
                // Hide unnecessary institutional panels
                document.getElementById('panel-rooms').classList.add('hidden');
                document.getElementById('panel-teachers').classList.add('hidden');
                document.getElementById('panel-enrollments').classList.add('hidden');
                document.querySelectorAll('.hide-in-student').forEach(el => el.classList.add('hidden'));
                
                // Adapt the Course panel into a Personal Subject Planner
                document.getElementById('course-panel-title').innerHTML = '<i class="fas fa-book-open mr-2 text-cyan-400"></i>Subjects / Tasks';
                document.getElementById('cr-code').placeholder = "Subject Name (e.g. Math)";
                document.getElementById('cr-enroll').value = 1; 
                document.getElementById('wrap-enroll').classList.add('hidden'); 
                document.getElementById('cr-type').classList.add('hidden'); 
                document.getElementById('cr-teacher').classList.add('hidden'); 
                document.getElementById('btn-course-submit').innerHTML = "Add Subject";
                
                // Center the 2 remaining panels elegantly
                document.getElementById('dashboard-grid').className = "flex justify-center gap-6 mb-8 transition-all";
                document.getElementById('panel-timeslots').style.width = "400px";
                document.getElementById('panel-courses').style.width = "400px";
                
                await fetchData();
                showToast('Personal Student Mode activated!', 'success');
                switchToDashboard();
            } catch (err) { showToast('Network error.', 'error'); document.getElementById('page-loader').classList.add('loader-hidden'); }
        }

        function switchToDashboard() {
            document.getElementById('landing-screen').classList.add('hidden');
            document.getElementById('main-dashboard').classList.remove('hidden');
            document.getElementById('results-container').classList.add('hidden');
            setTimeout(() => { document.getElementById('page-loader').classList.add('loader-hidden'); }, 400);
        }

        function backToHome() {
            document.getElementById('main-dashboard').classList.add('hidden');
            document.getElementById('landing-screen').classList.remove('hidden');
            // Reset grid layout so custom/template work perfectly next time
            document.getElementById('panel-timeslots').style.width = "auto";
            document.getElementById('panel-courses').style.width = "auto";
        }

        function selectDay(day) {
            selectedDay = day;
            document.querySelectorAll('.day-btn').forEach(btn => {
                btn.className = (btn.innerText === day) 
                    ? 'day-btn px-2 py-1 text-xs font-bold rounded bg-indigo-500 text-white transition' 
                    : 'day-btn px-2 py-1 text-xs font-bold rounded bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700 transition';
            });
        }

        async function fetchData() {
            try {
                const res = await fetch('/api/data');
                appData = await res.json();
                
                const makeLi = (icon, text, type, id) => `
                    <li class="group flex justify-between items-center py-1.5 px-2 rounded hover:bg-slate-800/60 transition-colors border-b border-transparent hover:border-slate-700">
                        <span class="truncate pr-2 text-slate-300 cursor-default" title="${text}">
                            <i class="fas ${icon} text-slate-500 mr-2"></i>${text}
                        </span>
                        <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
                            <button type="button" onclick="loadEdit('${type}', ${id})" class="w-6 h-6 flex items-center justify-center rounded-full bg-slate-800 text-amber-400 hover:bg-amber-500 hover:text-white border border-slate-700 hover:border-amber-500" title="Edit">
                                <i class="fas fa-pen" style="font-size: 0.6rem;"></i>
                            </button>
                            <button type="button" onclick="deleteItem('${type}', ${id})" class="w-6 h-6 flex items-center justify-center rounded-full bg-slate-800 text-slate-400 hover:bg-rose-500 hover:text-white border border-slate-700 hover:border-rose-500" title="Delete">
                                <i class="fas fa-times" style="font-size: 0.7rem;"></i>
                            </button>
                        </div>
                    </li>`;

                document.getElementById('list-timeslots').innerHTML = appData.timeslots.map(t => makeLi('fa-clock', t.name, 'timeslot', t.id)).join('');
                document.getElementById('list-rooms').innerHTML = appData.rooms.map(r => makeLi('fa-door-open', `${r.name} (Cap: ${r.capacity} | ${r.room_type})`, 'room', r.id)).join('');
                document.getElementById('list-teachers').innerHTML = (appData.teachers || []).map(t => makeLi('fa-chalkboard-teacher', `${t.name} (Max ${t.max_hours_per_day}/day)`, 'teacher', t.id)).join('');
                
                document.getElementById('list-courses').innerHTML = appData.courses.map(c => {
                    if(currentMode === 'student') return makeLi('fa-tasks', `${c.code} (${c.weekly_hours} hrs/wk)`, 'course', c.id);
                    return makeLi('fa-book', `${c.code} (${c.weekly_hours}x/wk | ${c.room_type})`, 'course', c.id);
                }).join('');
                
                document.getElementById('list-enrollments').innerHTML = appData.enrollments.map(e => makeLi('fa-user-graduate', `${e.student_id} -> ${e.course_code}`, 'enrollment', e.id)).join('');
                
                document.getElementById('en-course').innerHTML = '<option value="">Select Course...</option>' + appData.courses.map(c => `<option value="${c.id}">${c.code}</option>`).join('');
                document.getElementById('cr-teacher').innerHTML = '<option value="">Assign Teacher (Optional)</option>' + (appData.teachers || []).map(t => `<option value="${t.id}">${t.name}</option>`).join('');
            } catch (err) { showToast('Failed to fetch data.', 'error'); }
        }

        function loadEdit(type, id) {
            editState[type] = id;
            if (type === 'timeslot') {
                const item = appData.timeslots.find(t => t.id === id);
                // Reads string like "Mon 09:00 AM - 10:00 AM"
                const parts = item.name.split(' '); 
                if(parts.length >= 6) {
                    selectDay(parts[0]);
                    document.getElementById('time-start').value = parseTime(parts[1], parts[2]);
                    document.getElementById('time-end').value = parseTime(parts[4], parts[5]);
                    updateTimePreview();
                }
                const btn = document.getElementById('btn-timeslot-submit');
                btn.innerHTML = `<i class="fas fa-save mr-1"></i> Update`;
                btn.className = "w-full bg-amber-500/20 border border-amber-500/30 hover:bg-amber-500/40 text-amber-300 py-1.5 rounded text-sm font-semibold transition shadow-lg shadow-amber-500/20";
            } else {
                const form = document.querySelector(`form[onsubmit*="'${type}'"]`);
                if (form) {
                    const btn = form.querySelector('button[type="submit"]');
                    btn.innerHTML = `<i class="fas fa-save mr-1"></i> Update`;
                    btn.className = "w-full bg-amber-500/20 border border-amber-500/30 hover:bg-amber-500/40 text-amber-300 py-1.5 rounded text-sm font-semibold transition shadow-lg shadow-amber-500/20";
                }

                if (type === 'room') {
                    const item = appData.rooms.find(r => r.id === id);
                    document.getElementById('rm-name').value = item.name;
                    document.getElementById('rm-cap').value = item.capacity;
                    document.getElementById('rm-type').value = item.room_type;
                } else if (type === 'teacher') {
                    const item = appData.teachers.find(t => t.id === id);
                    document.getElementById('tc-name').value = item.name;
                    document.getElementById('tc-max').value = item.max_hours_per_day;
                } else if (type === 'course') {
                    const item = appData.courses.find(c => c.id === id);
                    document.getElementById('cr-code').value = item.code;
                    document.getElementById('cr-enroll').value = item.enrolled_count;
                    document.getElementById('cr-hours').value = item.weekly_hours;
                    document.getElementById('cr-type').value = item.room_type;
                    document.getElementById('cr-teacher').value = item.teacher_id || '';
                } else if (type === 'enrollment') {
                    const item = appData.enrollments.find(e => e.id === id);
                    document.getElementById('en-student').value = item.student_id;
                    document.getElementById('en-course').value = item.course_id;
                }
            }
        }

        async function submitTimeslot() {
            const isEdit = editState['timeslot'] !== null;
            if (isEdit && !appData.timeslots.some(t => t.id === editState['timeslot'])) {
                showToast('Action Failed: This data was already deleted.', 'error');
                return resetEditState('timeslot', 'btn-timeslot-submit');
            }
            try {
                await fetch(isEdit ? `/api/timeslot/${editState['timeslot']}` : '/api/timeslot', {
                    method: isEdit ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: document.getElementById('time-preview').innerText })
                });
                if (isEdit) resetEditState('timeslot', 'btn-timeslot-submit');
                fetchData();
                showToast(isEdit ? 'Timeslot updated!' : 'Timeslot added!', 'success');
            } catch (err) { showToast('Network error.', 'error'); }
        }

        async function addData(event, endpoint, type) {
            event.preventDefault();
            const isEdit = editState[type] !== null;
            
            if (isEdit) {
                const list = appData[type + 's']; 
                if (list && !list.some(i => i.id === editState[type])) {
                    showToast('Action Failed: This data was already deleted.', 'error');
                    resetEditState(type, null, event.target);
                    return;
                }
            }

            let payload = {};
            if (type === 'room') payload = { name: document.getElementById('rm-name').value, capacity: document.getElementById('rm-cap').value, room_type: document.getElementById('rm-type').value };
            if (type === 'teacher') payload = { name: document.getElementById('tc-name').value, max_hours_per_day: document.getElementById('tc-max').value };
            
            if (type === 'course') {
                const tid = document.getElementById('cr-teacher').value;
                payload = { 
                    code: document.getElementById('cr-code').value, 
                    enrolled_count: currentMode === 'student' ? 1 : document.getElementById('cr-enroll').value, 
                    weekly_hours: document.getElementById('cr-hours').value, 
                    room_type: currentMode === 'student' ? 'Classroom' : document.getElementById('cr-type').value, 
                    // In student mode, silently map to the auto-generated "Self Study" teacher (ID 1)
                    teacher_id: currentMode === 'student' ? 1 : (tid ? parseInt(tid) : null) 
                };
            }
            if (type === 'enrollment') payload = { student_id: document.getElementById('en-student').value, course_id: document.getElementById('en-course').value };

            try {
                await fetch(isEdit ? `${endpoint}/${editState[type]}` : endpoint, { method: isEdit ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (isEdit) resetEditState(type, null, event.target);
                else event.target.reset();
                fetchData(); 
                showToast(isEdit ? `${type} updated!` : `${type} added!`, 'success');
            } catch (err) { showToast('Network error.', 'error'); }
        }

        function resetEditState(type, btnId, formElement) {
            editState[type] = null;
            const btn = btnId ? document.getElementById(btnId) : formElement.querySelector('button[type="submit"]');
            btn.innerHTML = `Add Data`;
            btn.className = "w-full bg-indigo-500/20 border border-indigo-500/30 hover:bg-indigo-500/40 text-indigo-300 py-1.5 rounded text-sm font-semibold transition";
            if(formElement) formElement.reset();
        }

        async function deleteItem(endpoint, id) {
            try {
                await fetch(`/api/${endpoint}/${id}`, { method: 'DELETE' });
                fetchData();
            } catch (err) { showToast(`Failed to delete.`, 'error'); }
        }

        async function resetData() {
            document.getElementById('page-loader').classList.remove('loader-hidden');
            try {
                // If in student mode, clearing data just means we need to rebuild the silent dependencies
                if(currentMode === 'student') {
                    await fetch('/api/setup_student', { method: 'POST' });
                } else {
                    await fetch('/api/reset', { method: 'POST' });
                }
                document.getElementById('results-container').classList.add('hidden');
                await fetchData();
                showToast('All data cleared successfully.', 'success');
            } catch (err) { showToast('Failed to clear data.', 'error'); } 
            finally { setTimeout(() => { document.getElementById('page-loader').classList.add('loader-hidden'); }, 500); }
        }

        async function previewSchedule(btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-circle-notch fa-spin mr-2"></i> Optimizing...';
            try {
                const response = await fetch('/api/generate');
                const data = await response.json();
                
                if (data.status === 'Success') {
                    if (data.metrics) {
                        document.getElementById('metric-classes').innerText = data.metrics.total_classes;
                        document.getElementById('metric-utilization').innerText = data.metrics.room_utilization;
                        document.getElementById('metric-empty').innerText = data.metrics.empty_slots;
                    }

                    // Dynamically format table headers depending on the mode
                    const thead = document.getElementById('schedule-header');
                    if(currentMode === 'student') {
                        thead.innerHTML = `<th class="px-6 py-4 font-semibold">Timeslot</th><th class="px-6 py-4 font-semibold text-cyan-400">Study Task / Subject</th>`;
                    } else {
                        // Changed 'Teacher' to 'Teacher ID'
                        thead.innerHTML = `<th class="px-6 py-4 font-semibold">Timeslot</th><th class="px-6 py-4 font-semibold">Course</th><th class="px-6 py-4 font-semibold">Teacher ID</th><th class="px-6 py-4 font-semibold">Room</th><th class="px-6 py-4 font-semibold">Students</th>`;
                    }

                    const tbody = document.getElementById('schedule-body');
                    tbody.innerHTML = data.schedule.map(item => {
                        if (currentMode === 'student') {
                            return `<tr class="hover:bg-slate-800/50 transition-colors">
                                <td class="px-6 py-4 whitespace-nowrap font-medium text-slate-200">${item.Timeslot}</td>
                                <td class="px-6 py-4 whitespace-nowrap font-bold text-cyan-400">${item.Course}</td>
                            </tr>`;
                        } else {
                            return `<tr class="hover:bg-slate-800/50 transition-colors">
                                <td class="px-6 py-4 whitespace-nowrap font-medium text-slate-200">${item.Timeslot}</td>
                                <td class="px-6 py-4 whitespace-nowrap font-bold text-indigo-400">${item.Course}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-slate-300">
                                    <!-- Added hover tooltip (title) and a dashed underline to indicate it is hoverable -->
                                    <span class="cursor-help border-b border-dashed border-slate-500 pb-0.5 text-indigo-300" title="Teacher Name: ${item.TeacherName}">
                                        ${item.TeacherID}
                                    </span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-slate-300">${item.Room}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="bg-slate-800 border border-slate-700 text-slate-300 py-1 px-3 rounded-full text-xs font-semibold shadow-sm">
                                        <i class="fas fa-user-friends mr-1 text-slate-400"></i>${item.Students}
                                    </span>
                                </td>
                            </tr>`;
                        }
                    }).join('');
                        
                    const resultsContainer = document.getElementById('results-container');
                    resultsContainer.classList.remove('hidden');
                    setTimeout(() => { resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);

                    if (data.message && data.message.includes('Conflicts')) {
                        showToast(data.message, 'error'); 
                    } else {
                        showToast(data.message || 'Schedule optimized successfully!', 'success');
                    }
                } else {
                    document.getElementById('results-container').classList.add('hidden');
                    showToast(data.message, 'error');
                }
            } catch (error) { showToast('Network Error.', 'error'); } finally { btn.innerHTML = originalText; }
        }

        function exportCSV() {
            let csv = [];
            const rows = document.querySelectorAll("#schedule-table tr");
            for (let i = 0; i < rows.length; i++) {
                let row = [], cols = rows[i].querySelectorAll("td, th");
                for (let j = 0; j < cols.length; j++) row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
                csv.push(row.join(","));
            }
            const csvFile = new Blob([csv.join("\\n")], { type: "text/csv" });
            const downloadLink = document.createElement("a");
            downloadLink.download = "Space_Timetable.csv";
            downloadLink.href = window.URL.createObjectURL(csvFile);
            downloadLink.style.display = "none";
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            showToast('Excel (CSV) exported successfully!', 'success');
        }

        function exportPDF() {
            const element = document.getElementById('results-container');
            const tableWrapper = document.getElementById('pdf-wrapper');
            const originalWidth = element.style.width;
            const originalMargin = element.style.margin;
            element.style.width = '1050px';
            element.style.margin = '0';
            element.classList.add('pdf-mode', 'pdf-solid-bg');
            element.classList.remove('overflow-hidden');
            if (tableWrapper) tableWrapper.classList.remove('overflow-x-auto');

            html2pdf().set({
                margin: [0.5, 0.5, 0.5, 0.5],
                filename: currentMode === 'student' ? 'Personal_Study_Plan.pdf' : 'Space_Timetable.pdf',
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true, scrollX: 0, scrollY: 0 },
                jsPDF: { unit: 'in', format: 'letter', orientation: currentMode === 'student' ? 'portrait' : 'landscape' }
            }).from(element).save().then(() => {
                element.style.width = originalWidth;
                element.style.margin = originalMargin;
                element.classList.remove('pdf-mode', 'pdf-solid-bg');
                element.classList.add('overflow-hidden');
                if (tableWrapper) tableWrapper.classList.add('overflow-x-auto');
                showToast('PDF downloaded successfully!', 'success');
            });
        }
    </script>
</body>
</html>
"""

# ==========================================
# 3. ROUTES
# ==========================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/setup_dummy', methods=['POST'])
def setup_dummy():
    db.drop_all()
    db.create_all()
    
    # 1. Rooms
    rooms = [
        Room(name="Main Auditorium", capacity=350, room_type="Auditorium"),
        Room(name="Lecture Hall A", capacity=150, room_type="Classroom"),
        Room(name="Lecture Hall B", capacity=120, room_type="Classroom"),
        Room(name="Computer Lab", capacity=80, room_type="Lab"),
        Room(name="Seminar Room B", capacity=50, room_type="Classroom"),
        Room(name="Chemistry Lab", capacity=65, room_type="Lab"),
        Room(name="Science Lab 1", capacity=40, room_type="Lab"),
        Room(name="Forensics Lab", capacity=30, room_type="Lab"),
        Room(name="Small Classroom 1", capacity=25, room_type="Classroom"),
        Room(name="Small Classroom 2", capacity=25, room_type="Classroom")
    ]
    db.session.add_all(rooms)
    
    # 2. Teachers 
    teachers = [
        Teacher(name="Dr. Alam Shah", max_hours_per_day=4),
        Teacher(name="Prof. Mundan Kumar", max_hours_per_day=3),
        Teacher(name="Dr. Renuka Gupta", max_hours_per_day=5),
        Teacher(name="Prof. Ada Smith", max_hours_per_day=4),
        Teacher(name="Dr. Rajiv Chauhan", max_hours_per_day=4),
        Teacher(name="Prof. Geetanjali Verma", max_hours_per_day=3),
        Teacher(name="Dr. Prithvesh Singh", max_hours_per_day=4)
    ]
    db.session.add_all(teachers)
    db.session.flush() 
    
    # 3. Courses 
    c_cs101 = Course(code="CS-101", enrolled_count=120, weekly_hours=3, room_type="Classroom", teacher_id=teachers[0].id)
    c_law201 = Course(code="LAW-201", enrolled_count=110, weekly_hours=2, room_type="Auditorium", teacher_id=teachers[1].id)
    c_chem101 = Course(code="CHEM-101", enrolled_count=45, weekly_hours=2, room_type="Lab", teacher_id=teachers[2].id)
    c_his301 = Course(code="HIS-301", enrolled_count=80, weekly_hours=3, room_type="Classroom", teacher_id=teachers[3].id)
    c_phy101 = Course(code="PHY-101", enrolled_count=75, weekly_hours=2, room_type="Lab", teacher_id=teachers[4].id)
    c_stat101 = Course(code="STAT-101", enrolled_count=65, weekly_hours=2, room_type="Classroom", teacher_id=teachers[0].id)
    c_math202 = Course(code="MATH-202", enrolled_count=60, weekly_hours=3, room_type="Classroom", teacher_id=teachers[5].id)
    c_bio201 = Course(code="BIO-201", enrolled_count=50, weekly_hours=2, room_type="Lab", teacher_id=teachers[2].id)
    c_cs301 = Course(code="CS-301", enrolled_count=45, weekly_hours=2, room_type="Lab", teacher_id=teachers[0].id)
    c_eng101 = Course(code="ENG-101", enrolled_count=40, weekly_hours=3, room_type="Classroom", teacher_id=teachers[6].id)
    c_fs402 = Course(code="FS-402", enrolled_count=25, weekly_hours=1, room_type="Lab", teacher_id=teachers[1].id)
    c_fs501 = Course(code="FS-501", enrolled_count=20, weekly_hours=1, room_type="Lab", teacher_id=teachers[2].id)
    
    db.session.add_all([c_cs101, c_law201, c_chem101, c_his301, c_phy101, c_stat101, c_math202, c_bio201, c_cs301, c_eng101, c_fs402, c_fs501])
    
    # 4. Timeslots 
    db.session.add_all([
        Timeslot(name="Mon 09:00 AM - 10:00 AM"), Timeslot(name="Mon 11:00 AM - 12:00 PM"), Timeslot(name="Mon 02:00 PM - 03:00 PM"),
        Timeslot(name="Tue 09:00 AM - 10:00 AM"), Timeslot(name="Tue 11:00 AM - 12:00 PM"), Timeslot(name="Tue 02:00 PM - 03:00 PM"),
        Timeslot(name="Wed 09:00 AM - 10:00 AM"), Timeslot(name="Wed 11:00 AM - 12:00 PM"), Timeslot(name="Wed 02:00 PM - 03:00 PM"),
        Timeslot(name="Thu 09:00 AM - 10:00 AM"), Timeslot(name="Thu 11:00 AM - 12:00 PM"), Timeslot(name="Thu 02:00 PM - 03:00 PM"),
        Timeslot(name="Fri 09:00 AM - 10:00 AM"), Timeslot(name="Fri 11:00 AM - 12:00 PM"), Timeslot(name="Fri 02:00 PM - 03:00 PM")
    ])
    db.session.commit()

    # 5. Enrollments
    db.session.add_all([
        StudentEnrollment(student_id="STU_001", course_id=c_cs101.id),
        StudentEnrollment(student_id="STU_001", course_id=c_math202.id),
        StudentEnrollment(student_id="STU_001", course_id=c_phy101.id),
        StudentEnrollment(student_id="STU_002", course_id=c_cs101.id),
        StudentEnrollment(student_id="STU_002", course_id=c_stat101.id),
        StudentEnrollment(student_id="STU_003", course_id=c_bio201.id),
        StudentEnrollment(student_id="STU_003", course_id=c_chem101.id),
        StudentEnrollment(student_id="STU_003", course_id=c_fs501.id)
    ])
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/setup_student', methods=['POST'])
def setup_student():
    # Secretly sets up dependencies so the user can just use timeslots & subjects
    db.drop_all()
    db.create_all()
    
    room = Room(name="Personal Workspace", capacity=1, room_type="Classroom")
    teacher = Teacher(name="Self Study", max_hours_per_day=24)
    db.session.add_all([room, teacher])
    db.session.commit()
    return jsonify({"status": "success"})


@app.route('/api/reset', methods=['POST'])
def reset_data():
    db.drop_all()
    db.create_all()
    return jsonify({"status": "success"})

@app.route('/api/data', methods=['GET'])
def get_all_data():
    return jsonify({
        "teachers": [{"id": t.id, "name": t.name, "max_hours_per_day": t.max_hours_per_day} for t in Teacher.query.all()],
        "rooms": [{"id": r.id, "name": r.name, "capacity": r.capacity, "room_type": r.room_type} for r in Room.query.all()],
        "courses": [{"id": c.id, "code": c.code, "enrolled_count": c.enrolled_count, "weekly_hours": c.weekly_hours, "room_type": c.room_type, "teacher_id": c.teacher_id} for c in Course.query.all()],
        "timeslots": [{"id": t.id, "name": t.name} for t in Timeslot.query.all()],
        "enrollments": [{"id": e.id, "student_id": e.student_id, "course_id": e.course_id, "course_code": getattr(db.session.get(Course, e.course_id), 'code', 'Unknown')} for e in StudentEnrollment.query.all()]
    })

# API Routes for Creation & Updating
@app.route('/api/room', methods=['POST'])
def add_room():
    db.session.add(Room(name=request.json.get('name'), capacity=int(request.json.get('capacity')), room_type=request.json.get('room_type', 'Classroom')))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/room/<int:item_id>', methods=['PUT', 'DELETE'])
def handle_room(item_id):
    item = Room.query.get(item_id)
    if not item: return jsonify({"status": "error"}), 404
    if request.method == 'PUT':
        item.name = request.json.get('name')
        item.capacity = int(request.json.get('capacity'))
        item.room_type = request.json.get('room_type', 'Classroom')
    elif request.method == 'DELETE':
        db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/teacher', methods=['POST'])
def add_teacher():
    db.session.add(Teacher(name=request.json.get('name'), max_hours_per_day=int(request.json.get('max_hours_per_day', 4))))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/teacher/<int:item_id>', methods=['PUT', 'DELETE'])
def handle_teacher(item_id):
    item = Teacher.query.get(item_id)
    if not item: return jsonify({"status": "error"}), 404
    if request.method == 'PUT':
        item.name = request.json.get('name')
        item.max_hours_per_day = int(request.json.get('max_hours_per_day', 4))
    elif request.method == 'DELETE':
        Course.query.filter_by(teacher_id=item_id).update({"teacher_id": None})
        db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/course', methods=['POST'])
def add_course():
    tid = request.json.get('teacher_id')
    db.session.add(Course(code=request.json.get('code'), enrolled_count=int(request.json.get('enrolled_count')), weekly_hours=int(request.json.get('weekly_hours', 1)), room_type=request.json.get('room_type', 'Classroom'), teacher_id=tid if tid else None))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/course/<int:item_id>', methods=['PUT', 'DELETE'])
def handle_course(item_id):
    item = Course.query.get(item_id)
    if not item: return jsonify({"status": "error"}), 404
    if request.method == 'PUT':
        item.code = request.json.get('code')
        item.enrolled_count = int(request.json.get('enrolled_count'))
        item.weekly_hours = int(request.json.get('weekly_hours', 1))
        item.room_type = request.json.get('room_type', 'Classroom')
        tid = request.json.get('teacher_id')
        item.teacher_id = tid if tid else None
    elif request.method == 'DELETE':
        StudentEnrollment.query.filter_by(course_id=item_id).delete()
        db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/enrollment', methods=['POST'])
def add_enrollment():
    db.session.add(StudentEnrollment(student_id=request.json.get('student_id'), course_id=int(request.json.get('course_id'))))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/enrollment/<int:item_id>', methods=['PUT', 'DELETE'])
def handle_enrollment(item_id):
    item = StudentEnrollment.query.get(item_id)
    if not item: return jsonify({"status": "error"}), 404
    if request.method == 'PUT':
        item.student_id = request.json.get('student_id')
        item.course_id = int(request.json.get('course_id'))
    elif request.method == 'DELETE':
        db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/timeslot', methods=['POST'])
def add_timeslot():
    db.session.add(Timeslot(name=request.json.get('name')))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/timeslot/<int:item_id>', methods=['PUT', 'DELETE'])
def handle_timeslot(item_id):
    item = Timeslot.query.get(item_id)
    if not item: return jsonify({"status": "error"}), 404
    if request.method == 'PUT':
        item.name = request.json.get('name')
    elif request.method == 'DELETE':
        db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success"})


# ==========================================
# 4. RANDOMIZED HEURISTIC SCHEDULING ENGINE
# ==========================================
@app.route('/api/generate', methods=['GET'])
def generate_schedule():
    courses = Course.query.all()
    rooms = Room.query.all()
    timeslots = Timeslot.query.all()
    enrollments = StudentEnrollment.query.all()

    if not courses or not rooms or not timeslots:
        return jsonify({"status": "Error", "message": "Must have at least 1 course, room, and timeslot to schedule."})

    # Pre-process Data Dictionaries for fast lookups
    student_to_courses = {}
    for e in enrollments:
        student_to_courses.setdefault(e.student_id, []).append(e.course_id)

    course_to_students = {}
    for c in courses:
        course_to_students[c.id] = set([s for s, c_list in student_to_courses.items() if c.id in c_list])

    teachers_dict = {t.id: t for t in Teacher.query.all()}

    # State Tracking
    timetable = {}         # key: (timeslot_id, room_id), value: course_id
    teacher_schedule = {}  # key: (timeslot_id, teacher_id), value: course_id
    teacher_daily_hrs = {} # key: (day_string, teacher_id), value: int
    student_schedule = {}  # key: (timeslot_id, student_id), value: course_id
    
    conflicts = []
    schedule_output = []

    # Algorithm: Sort courses by workload/difficulty (highest enrollment first)
    sorted_courses = sorted(courses, key=lambda c: c.enrolled_count, reverse=True)

    for course in sorted_courses:
        hours_scheduled = 0
        attempts = 0
        max_attempts = 300  # Prevent infinite loops on impossible schedules

        while hours_scheduled < course.weekly_hours and attempts < max_attempts:
            attempts += 1
            t = random.choice(timeslots)
            r = random.choice(rooms)
            
            # Timeslots are expected to be strings like "Mon 09:00 AM". Split to get the Day.
            day_str = t.name.split(' ')[0] if ' ' in t.name else 'Any'

            # --- CONSTRAINT CHECKS ---
            
            # 1. Room Restrictions
            if r.room_type != course.room_type: 
                continue
            if r.capacity < course.enrolled_count: 
                continue
            if (t.id, r.id) in timetable: 
                continue

            # 2. Teacher Restrictions
            if course.teacher_id:
                if (t.id, course.teacher_id) in teacher_schedule: 
                    continue
                teacher_obj = teachers_dict.get(course.teacher_id)
                if teacher_obj and teacher_daily_hrs.get((day_str, course.teacher_id), 0) >= teacher_obj.max_hours_per_day:
                    continue

            # 3. Student Restrictions
            student_conflict = False
            for student in course_to_students.get(course.id, []):
                if (t.id, student) in student_schedule:
                    student_conflict = True
                    break
            if student_conflict:
                continue

            # --- ASSIGNMENT SUCESSFUL ---
            timetable[(t.id, r.id)] = course.id
            if course.teacher_id:
                teacher_schedule[(t.id, course.teacher_id)] = course.id
                teacher_daily_hrs[(day_str, course.teacher_id)] = teacher_daily_hrs.get((day_str, course.teacher_id), 0) + 1
            for student in course_to_students.get(course.id, []):
                student_schedule[(t.id, student)] = course.id

            teacher_obj = teachers_dict.get(course.teacher_id)
            schedule_output.append({
                "Timeslot": t.name,
                "Course": course.code,
                # Format the DB integer ID to look like "TCH-001"
                "TeacherID": f"TCH-{teacher_obj.id:03d}" if teacher_obj else "N/A",
                "TeacherName": teacher_obj.name if teacher_obj else "No Teacher Assigned",
                "Room": r.name,
                "Students": course.enrolled_count
            })
            hours_scheduled += 1

        # Track unplaced constraints (Conflicts)
        if hours_scheduled < course.weekly_hours:
            conflicts.append(f"{course.code} ({hours_scheduled}/{course.weekly_hours} hrs)")

    # Sort final schedule output nicely by timeslot string
    schedule_output = sorted(schedule_output, key=lambda x: x["Timeslot"])

    # Dashboard Metrics
    total_slots = len(timeslots) * len(rooms)
    used_slots = len(schedule_output)
    utilization = round((used_slots / total_slots * 100), 1) if total_slots > 0 else 0

    metrics = {
        "total_classes": used_slots,
        "room_utilization": f"{utilization}%",
        "empty_slots": total_slots - used_slots
    }

    # Format the final notification message
    if conflicts:
        message = f"⚠️ Partial Schedule Generated. Conflicts (could not fit): {', '.join(conflicts)}"
    else:
        message = "Schedule optimized successfully with zero conflicts!"

    return jsonify({"status": "Success", "schedule": schedule_output, "metrics": metrics, "message": message})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("UI is ready! Open http://127.0.0.1:5001/ in your browser.")
    app.run(debug=True, use_reloader=False, port=5001)
