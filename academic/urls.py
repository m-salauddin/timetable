from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet, SemesterViewSet, CourseViewSet, 
    TimeSlotViewSet, GenerateRoutineView, RoutineListView
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'semesters', SemesterViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'timeslots', TimeSlotViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('generate-routine/', GenerateRoutineView.as_view(), name='generate-routine'),
    path('view-routine/', RoutineListView.as_view(), name='view-routine'),
]