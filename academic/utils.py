from .models import Course, TimeSlot, RoutineEntry
import random
from django.db import transaction
from django.db.models import F
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


    def is_conflict(self, day, slot, course):
       
        if course.teacher and (day, slot.id, course.teacher.id) in self.teacher_occupied:
            return True
        
        if (day, slot.id, course.room_number) in self.room_occupied:
            return True
        
        if (day, slot.id, course.department.id, course.semester.id) in self.batch_occupied:
            return True

     
        if (course.id, day) in self.course_daily_tracker:
            return True

     
        if course.teacher:
            tb_key = (day, course.teacher.id, course.department.id, course.semester.id)
            if tb_key in self.teacher_batch_interaction:
                existing_course_id = self.teacher_batch_interaction[tb_key]
              
                if existing_course_id != course.id:
                    return True 
        return False

 
    def assign(self, day, slot, course):
        if course.teacher:
            self.teacher_occupied.add((day, slot.id, course.teacher.id))
      
            tb_key = (day, course.teacher.id, course.department.id, course.semester.id)
            self.teacher_batch_interaction[tb_key] = course.id
           
            t_key = (course.teacher.id, day)
            self.teacher_daily_count[t_key] = self.teacher_daily_count.get(t_key, 0) + 1

        self.room_occupied.add((day, slot.id, course.room_number))
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
                priority_score = credits_filled / total_credits
                all_sessions.append({
                    'course': course, 
                    'duration': 1, 
                    'priority_score': priority_score,
                    'is_lab': True
                })
        else:
            for _ in range(remaining_credits):
                credits_filled += 1
                priority_score = credits_filled / total_credits
                all_sessions.append({
                    'course': course, 
                    'duration': 1, 
                    'priority_score': priority_score,
                    'is_lab': False
                })
    

    random.shuffle(all_sessions) 
    all_sessions.sort(key=lambda x: (x['priority_score'], -x['duration']))
    
    return all_sessions


def generate_routine_algorithm():

    RoutineEntry.objects.all().delete()
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']

    time_slots = list(TimeSlot.objects.all().order_by('start_time'))
    courses = list(Course.objects.all())


    sorted_sessions = prepare_prioritized_sessions(courses)
    constraints = ScheduleConstraint(days)
    
    scheduled_count = 0
    dropped_sessions = []

    
    for session in sorted_sessions:
        course = session['course']
        duration = session['duration']
        assigned = False
        
  
        def get_day_score(d):
           
            b_load = constraints.get_batch_daily_load(d, course.department.id, course.semester.id)
    
            t_load = constraints.get_teacher_daily_load(d, course.teacher.id) if course.teacher else 0
          
            g_load = constraints.day_loads[d]
            
            return (b_load * 15) + (t_load * 10) + g_load

       
        sorted_days = sorted(days, key=get_day_score)

        for day in sorted_days:
            if assigned: break
            
    
            for i in range(len(time_slots) - duration + 1):
                slots_to_check = []
                conflict = False

                for j in range(duration):
                    slot = time_slots[i + j]
               
                    if constraints.is_conflict(day, slot, course):
                        conflict = True; break
                    slots_to_check.append(slot)
                
                if not conflict:
                    
                    for slot in slots_to_check:
                        constraints.assign(day, slot, course)
                        RoutineEntry.objects.create(day=day, time_slot=slot, course=course)
                    
                    assigned = True
                    scheduled_count += 1
                    break 
        
        if not assigned:
           
            percent = int(session['priority_score'] * 100)
            dropped_sessions.append(f"{course.course_name} ({percent}% Completed) - Resource Shortage")

    return {
        "status": "Completed",
        "total_sessions": len(sorted_sessions),
        "scheduled": scheduled_count,
        "dropped": len(dropped_sessions),
        "dropped_details": dropped_sessions,
        "message": "Routine generated ensuring no overlaps and prioritized scheduling."
    }