from .models import Course, TimeSlot, RoutineEntry, Room
import random
from django.db import transaction
from collections import Counter

class ScheduleConstraint:
    def __init__(self, days):
        self.teacher_occupied = set()    
        self.room_occupied = set()        
        self.batch_occupied = set()      
        self.course_daily_tracker = set() 
        self.teacher_batch_interaction = {}
     
        self.day_loads = {day: 0 for day in days} 
        self.teacher_daily_count = {} 
        self.batch_daily_count = {}   

    def get_teacher_daily_load(self, day, teacher_id):
        if not teacher_id: return 0
        return self.teacher_daily_count.get((teacher_id, day), 0)

    def get_batch_daily_load(self, day, dept_id, sem_id):
        return self.batch_daily_count.get((dept_id, sem_id, day), 0)

    def is_conflict(self, day, slot, course, room):
        # Teacher conflict
        if course.teacher and (day, slot.id, course.teacher.id) in self.teacher_occupied:
            return True
        
  
        if room and (day, slot.id, room.id) in self.room_occupied:
            return True
        
        # Batch conflict
        if (day, slot.id, course.department.id, course.semester.id) in self.batch_occupied:
            return True

        # Course daily limit
        if (course.id, day) in self.course_daily_tracker:
            return True

        # Teacher batch continuity
        if course.teacher:
            tb_key = (day, course.teacher.id, course.department.id, course.semester.id)
            if tb_key in self.teacher_batch_interaction:
                existing_course_id = self.teacher_batch_interaction[tb_key]
                if existing_course_id != course.id:
                    return True 
        return False


    def assign(self, day, slot, course, room):
        if course.teacher:
            self.teacher_occupied.add((day, slot.id, course.teacher.id))
            tb_key = (day, course.teacher.id, course.department.id, course.semester.id)
            self.teacher_batch_interaction[tb_key] = course.id
            t_key = (course.teacher.id, day)
            self.teacher_daily_count[t_key] = self.teacher_daily_count.get(t_key, 0) + 1

        if room:
            self.room_occupied.add((day, slot.id, room.id))
            
        self.batch_occupied.add((day, slot.id, course.department.id, course.semester.id))
        self.course_daily_tracker.add((course.id, day))
        
        self.day_loads[day] += 1
        b_key = (course.department.id, course.semester.id, day)
        self.batch_daily_count[b_key] = self.batch_daily_count.get(b_key, 0) + 1


def prepare_prioritized_sessions(courses):
    all_sessions = []
    
    for course in courses:
        total_credits = course.credits if course.credits > 0 else 1
        credits_filled = 0 
        remaining_credits = course.credits
        
        if course.course_type == 'Lab':
            while remaining_credits >= 2:
                credits_filled += 2
                priority_score = credits_filled / total_credits 
                all_sessions.append({
                    'course': course, 
                    'duration': 2, 
                    'priority_score': priority_score,
                    'is_lab': True
                })
                remaining_credits -= 2
           
            if remaining_credits > 0:
                credits_filled += 1
                all_sessions.append({
                    'course': course, 
                    'duration': 1, 
                    'priority_score': credits_filled / total_credits,
                    'is_lab': True
                })
        else:
            for _ in range(remaining_credits):
                credits_filled += 1
                all_sessions.append({
                    'course': course, 
                    'duration': 1, 
                    'priority_score': credits_filled / total_credits,
                    'is_lab': False
                })
    
    random.shuffle(all_sessions) 
    all_sessions.sort(key=lambda x: (x['priority_score'], -x['duration']))
    return all_sessions


def generate_routine_algorithm(department_id):

    RoutineEntry.objects.filter(course__department_id=department_id).delete()
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    time_slots = list(TimeSlot.objects.all().order_by('start_time'))
    
    
    courses = list(Course.objects.filter(department_id=department_id))
    all_rooms = list(Room.objects.all())

    constraints = ScheduleConstraint(days)
    
   
    existing_routines = RoutineEntry.objects.exclude(course__department_id=department_id)
    for r in existing_routines:
        constraints.assign(r.day, r.time_slot, r.course, r.room)

    sorted_sessions = prepare_prioritized_sessions(courses)
    scheduled_count = 0
    dropped_sessions = []

    for session in sorted_sessions:
        course = session['course']
        duration = session['duration']
        assigned = False
        
        # অ্যাডমিন ওভাররাইড চেক
        allowed_days = [course.fixed_day] if course.fixed_day else days
        
        # রুম ফিল্টারিং লজিক
        if course.fixed_room:
            valid_rooms = [course.fixed_room]
        else:
            valid_rooms = []
            for r in all_rooms:
                if r.capacity < course.student_count: continue
                if r.room_type != course.course_type: continue
                if course.sub_category and r.sub_category != course.sub_category: continue
                if r.department and r.department_id != course.department_id: continue
                valid_rooms.append(r)
            # ছোট রুমগুলো আগে ফিলআপ করার জন্য ক্যাপাসিটি অনুযায়ী সর্ট
            valid_rooms.sort(key=lambda x: x.capacity)
            
        if not valid_rooms:
            dropped_sessions.append(f"{course.course_name} - উপযুক্ত কোনো রুম পাওয়া যায়নি")
            continue

        # লোড ব্যালেন্সিং
        if not course.fixed_day:
            def get_day_score(d):
                b_load = constraints.get_batch_daily_load(d, course.department.id, course.semester.id)
                t_load = constraints.get_teacher_daily_load(d, course.teacher.id) if course.teacher else 0
                g_load = constraints.day_loads[d]
                return (b_load * 15) + (t_load * 10) + g_load
            sorted_days = sorted(allowed_days, key=get_day_score)
        else:
            sorted_days = allowed_days

        for day in sorted_days:
            if assigned: break
            
            for i in range(len(time_slots) - duration + 1):
                if assigned: break
                
                start_slot = time_slots[i]
                
                # অ্যাডমিন টাইম স্লট ওভাররাইড চেক
                if course.fixed_time_slot and start_slot.id != course.fixed_time_slot.id:
                    continue

                window_slots = time_slots[i : i + duration]
                selected_room = None

                # চেক করা হচ্ছে কোন রুমটি কনফ্লিক্ট ছাড়া ফ্রি আছে
                for room in valid_rooms:
                    room_conflict = False
                    for slot in window_slots:
                        if constraints.is_conflict(day, slot, course, room):
                            room_conflict = True
                            break
                    
                    if not room_conflict:
                        selected_room = room
                        break 
                
                if selected_room:
                    for slot in window_slots:
                        constraints.assign(day, slot, course, selected_room)
                        RoutineEntry.objects.create(day=day, time_slot=slot, course=course, room=selected_room)
                    
                    assigned = True
                    scheduled_count += 1

        if not assigned:
            percent = int(session['priority_score'] * 100)
            dropped_sessions.append(f"{course.course_name} ({percent}% Completed) - শিডিউল কনফ্লিক্ট বা টাইম স্লট নেই")

    return {
        "status": "Completed",
        "total_sessions": len(sorted_sessions),
        "scheduled": scheduled_count,
        "dropped": len(dropped_sessions),
        "dropped_details": dropped_sessions,
        "message": "Routine generated successfully for the selected department."
    }