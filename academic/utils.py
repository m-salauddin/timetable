from django.db import transaction
from django.db.models import F
from collections import Counter
import random
from .models import Course, TimeSlot, RoutineEntry

class ScheduleConstraint:
    def __init__(self, days):
        self.teacher_occupied = set()      # (day, slot_id, teacher_id)
        self.room_occupied = set()         # (day, slot_id, room_number)
        self.batch_occupied = set()        # (day, slot_id, dept_id, sem_id)
        self.course_daily_tracker = set()  # (course_id, day)
        self.day_loads = {day: 0 for day in days} 

    def check_conflict_reason(self, day, slot, course):
    
        if course.teacher and (day, slot.id, course.teacher.id) in self.teacher_occupied:
            return "Teacher Busy"
        
  
        if course.room_number and (day, slot.id, course.room_number) in self.room_occupied:
            return "Room Busy"
            
 
        if (day, slot.id, course.department.id, course.semester.id) in self.batch_occupied:
            return "Batch Busy"

    
        if course.course_type == 'Theory':
            if (course.id, day) in self.course_daily_tracker:
                return "Daily Limit Reached"
        
        return None

    def assign(self, day, slot, course):
        if course.teacher:
            self.teacher_occupied.add((day, slot.id, course.teacher.id))
        
        if course.room_number:
            self.room_occupied.add((day, slot.id, course.room_number))
            
        self.batch_occupied.add((day, slot.id, course.department.id, course.semester.id))
        
        if course.course_type == 'Theory':
            self.course_daily_tracker.add((course.id, day))
            
        self.day_loads[day] += 1

def prepare_prioritized_sessions(courses):
    all_sessions = []
    for course in courses:
        remaining_credits = course.credits
        class_rank = 1 
        
       
        if course.course_type == 'Lab':
            while remaining_credits >= 2:
                all_sessions.append({'course': course, 'duration': 2, 'priority': class_rank})
                remaining_credits -= 2
                class_rank += 1
        
            if remaining_credits > 0:
                all_sessions.append({'course': course, 'duration': 1, 'priority': class_rank})
        
     
        else:
            for _ in range(remaining_credits):
                all_sessions.append({'course': course, 'duration': 1, 'priority': class_rank})
                class_rank += 1
   
    random.shuffle(all_sessions)
    all_sessions.sort(key=lambda x: (x['priority'], -x['duration']))
    return all_sessions

def generate_routine_algorithm():
   
    with transaction.atomic():
     
        RoutineEntry.objects.all().delete()

        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
        
   
        time_slots = list(TimeSlot.objects.all().order_by('start_time'))
        
        courses = list(Course.objects.select_related('teacher', 'department', 'semester').all())
        
        sorted_sessions = prepare_prioritized_sessions(courses)
        constraints = ScheduleConstraint(days)
        
        scheduled_count = 0
        dropped_sessions_details = []

        for session in sorted_sessions:
            course = session['course']
            duration = session['duration']
            priority = session['priority']
            
            assigned = False
            failure_reasons = []
            
            
            sorted_days = sorted(days, key=lambda d: constraints.day_loads[d])

            for day in sorted_days:
                if assigned: break

           
                for i in range(len(time_slots) - duration + 1):
                    slots_to_check = []
                    conflict_reason = None
                    
                    for j in range(duration):
                        slot = time_slots[i + j]
                        reason = constraints.check_conflict_reason(day, slot, course)
                        if reason:
                            conflict_reason = reason
                            break
                        slots_to_check.append(slot)
                    
                    if not conflict_reason:
                    
                        for slot in slots_to_check:
                            constraints.assign(day, slot, course)
                            
                           
                            RoutineEntry.objects.create(
                                day=day,
                                time_slot=slot,
                                course=course
                            )
                        
                        assigned = True
                        scheduled_count += 1
                        break 
                    else:
                        failure_reasons.append(conflict_reason)
            
            if not assigned:
                
                reason_counts = Counter(failure_reasons)
                dropped_sessions_details.append(f"{course.course_name} (Round {priority}) - Failed. Reasons: {dict(reason_counts)}")

        return {
            "status": "Completed",
            "total_sessions_attempted": len(sorted_sessions),
            "successfully_scheduled": scheduled_count,
            "dropped_sessions_count": len(dropped_sessions_details),
            "dropped_details": dropped_sessions_details
        }













# from .models import Course, TimeSlot, RoutineEntry
# import random

# class ScheduleConstraint:
#     def __init__(self):
#         self.teacher_occupied = set()
#         self.room_occupied = set()
#         self.batch_occupied = set() # Batch = Dept + Semester

#     def is_conflict(self, day, slot, course):
#         if course.teacher and (day, slot.id, course.teacher.id) in self.teacher_occupied:
#             return True
#         if (day, slot.id, course.room_number) in self.room_occupied:
#             return True
        
#         if (day, slot.id, course.department.id, course.semester.id) in self.batch_occupied:
#             return True
#         return False

#     def assign(self, day, slot, course):
#         if course.teacher:
#             self.teacher_occupied.add((day, slot.id, course.teacher.id))
#         self.room_occupied.add((day, slot.id, course.room_number))
#         self.batch_occupied.add((day, slot.id, course.department.id, course.semester.id))

#     def remove(self, day, slot, course):
#         if course.teacher and (day, slot.id, course.teacher.id) in self.teacher_occupied:
#             self.teacher_occupied.remove((day, slot.id, course.teacher.id))
#         if (day, slot.id, course.room_number) in self.room_occupied:
#             self.room_occupied.remove((day, slot.id, course.room_number))
#         if (day, slot.id, course.department.id, course.semester.id) in self.batch_occupied:
#             self.batch_occupied.remove((day, slot.id, course.department.id, course.semester.id))


# def backtrack_schedule(session_idx, sessions, days, time_slots, constraints, scheduled_entries):
    
#     if session_idx >= len(sessions):
#         return True 

#     current_session = sessions[session_idx]
#     course = current_session['course']
#     duration = current_session['duration']


#     for day in days:
#         for i in range(len(time_slots) - duration + 1):
            
#             slots_to_check = []
#             conflict_found = False
            
#             for j in range(duration):
#                 slot = time_slots[i + j]
#                 if constraints.is_conflict(day, slot, course):
#                     conflict_found = True
#                     break
#                 slots_to_check.append(slot)
            
#             if not conflict_found:
#                 for slot in slots_to_check:
#                     constraints.assign(day, slot, course)
#                     scheduled_entries.append({
#                         'day': day,
#                         'time_slot': slot,
#                         'course': course
#                     })
                
#                 if backtrack_schedule(session_idx + 1, sessions, days, time_slots, constraints, scheduled_entries):
#                     return True

#                 for slot in slots_to_check:
#                     constraints.remove(day, slot, course)
#                     scheduled_entries.pop() 

#     return False 

# def prepare_sessions(courses):
#     lab_sessions = []
#     theory_sessions = []

#     for course in courses:
#         remaining_credits = course.credits
        
#         if course.course_type == 'Lab':
#             if remaining_credits == 2:
#                 lab_sessions.append({'course': course, 'duration': 2})
#             elif remaining_credits == 3:
#                 lab_sessions.append({'course': course, 'duration': 2})
#                 theory_sessions.append({'course': course, 'duration': 1})
#             elif remaining_credits == 4:
#                 lab_sessions.append({'course': course, 'duration': 2})
#                 lab_sessions.append({'course': course, 'duration': 2})
#             else:
#                 for _ in range(remaining_credits):
#                     theory_sessions.append({'course': course, 'duration': 1})
#         else:
#             for _ in range(remaining_credits):
#                 theory_sessions.append({'course': course, 'duration': 1})
    
#     return lab_sessions + theory_sessions


# def generate_routine_algorithm():
#     RoutineEntry.objects.all().delete()

#     days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
#     time_slots = list(TimeSlot.objects.all().order_by('start_time'))
    
#     all_courses = list(Course.objects.all())
#     random.shuffle(all_courses)

#     sessions = prepare_sessions(all_courses)

#     constraints = ScheduleConstraint()
#     final_schedule = []

   
    
#     success = backtrack_schedule(0, sessions, days, time_slots, constraints, final_schedule)

#     for entry in final_schedule:
#         RoutineEntry.objects.create(
#             day=entry['day'],
#             time_slot=entry['time_slot'],
#             course=entry['course']
#         )

#     status_msg = "Success" if success else "Partial Success (Could not fit all classes due to conflicts)"
    
#     return {
#         "status": status_msg,
#         "total_sessions_needed": len(sessions),
#         "sessions_scheduled": len(final_schedule),
#         "message": "Routine generated with Credit and Lab Constraints."
#     }