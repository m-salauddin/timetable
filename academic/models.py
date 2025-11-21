from django.db import models
from django.conf import settings

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Semester(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(unique=True)
    def __str__(self): return self.name

class Course(models.Model):
    COURSE_TYPES = (
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    )

    course_code = models.CharField(max_length=20, unique=True) 
    course_name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        limit_choices_to={'role': 'TEACHER'}
    )
    room_number = models.CharField(max_length=50)
    
    
    
    
    credits = models.IntegerField(default=3, help_text="Number of classes per week")
    course_type = models.CharField(max_length=10, choices=COURSE_TYPES, default='Theory')

    def __str__(self):
        return f"{self.course_code} - {self.course_name} ({self.course_type})"

class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

class RoutineEntry(models.Model):
    DAY_CHOICES = (
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
    )

    day = models.CharField(max_length=15, choices=DAY_CHOICES)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('day', 'time_slot', 'course')

    # def __str__(self):
    #     return f"{self.day} | {self.time_slot} | {self.course}"
    
    
    
    def __str__(self):
        return (
        f"{self.day} | "
        f"{self.time_slot} | "
        f"{self.course.department.name if self.course and self.course.department else 'No Dept'} "
        f"({self.course.semester.name if self.course and self.course.semester else 'No Semester'}) | "
        f"{self.course.course_name if self.course else 'No Course'} | "
        f"Room: {self.course.room_number if self.course else 'N/A'}"
         )

    
