from django.db import models
from django.conf import settings

# DAY_CHOICES কে উপরে নিয়ে আসলাম যাতে একাধিক জায়গায় ব্যবহার করা যায়
DAY_CHOICES = (
    ('Sunday', 'Sunday'),
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
)

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Semester(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(unique=True)
    def __str__(self): return self.name

class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

# ১. নতুন Room মডেল তৈরি
class Room(models.Model):
    ROOM_TYPES = (
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    )
    room_number = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField(help_text="এই রুমের ছাত্র ধারণক্ষমতা")
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='Theory')
    sub_category = models.CharField(max_length=100, null=True, blank=True, help_text="যেমন: Computer Lab, Electronics Lab (ঐচ্ছিক)")
    
    # রুমটি যদি নির্দিষ্ট কোনো ডিপার্টমেন্টের হয় (ঐচ্ছিক)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.room_number} ({self.room_type} - Cap: {self.capacity})"

# ২. Course মডেল আপডেট
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
    
    # ডিলিট করা হয়েছে: room_number = models.CharField(...)
    
    # নতুন যোগ করা হয়েছে: লজিক অনুযায়ী
    student_count = models.PositiveIntegerField(default=0, help_text="এই কোর্সে মোট ছাত্র সংখ্যা")
    credits = models.IntegerField(default=3, help_text="Number of classes per week")
    course_type = models.CharField(max_length=10, choices=COURSE_TYPES, default='Theory')
    sub_category = models.CharField(max_length=100, null=True, blank=True, help_text="ল্যাব হলে স্পেসিফিক ক্যাটাগরি (যেমন: Computer Lab)")

    # নতুন যোগ করা হয়েছে: অ্যাডমিন ওভাররাইড (অ্যাডমিন চাইলে নির্দিষ্ট করে দিতে পারে)
    fixed_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, help_text="অ্যাডমিন চাইলে এই কোর্সের জন্য নির্দিষ্ট রুম ফিক্সড করতে পারে")
    fixed_day = models.CharField(max_length=15, choices=DAY_CHOICES, null=True, blank=True, help_text="অ্যাডমিন চাইলে নির্দিষ্ট দিন ফিক্সড করতে পারে")
    fixed_time_slot = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True, help_text="অ্যাডমিন চাইলে নির্দিষ্ট টাইম স্লট ফিক্সড করতে পারে")

    def __str__(self):
        return f"{self.course_code} - {self.course_name} ({self.course_type})"

# ৩. RoutineEntry মডেল আপডেট
class RoutineEntry(models.Model):
    day = models.CharField(max_length=15, choices=DAY_CHOICES)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    # নতুন যোগ করা হয়েছে: অ্যালগরিদম এখানে রুম অ্যাসাইন করবে
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        # একই দিনে, একই সময়ে, একই রুমে একাধিক ক্লাস হতে পারবে না (কনফ্লিক্ট রোধ)
        unique_together = (('day', 'time_slot', 'room'), ('day', 'time_slot', 'course'))

    def __str__(self):
        dept_name = self.course.department.name if self.course and self.course.department else 'No Dept'
        sem_name = self.course.semester.name if self.course and self.course.semester else 'No Semester'
        course_name = self.course.course_name if self.course else 'No Course'
        # আপডেটেড রুমের নাম
        room_name = self.room.room_number if self.room else 'Unassigned'
        
        return f"{self.day} | {self.time_slot} | {dept_name} ({sem_name}) | {course_name} | Room: {room_name}"