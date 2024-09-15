from dataclasses import dataclass, field
from datetime import datetime
from INSOAPIQuery.utils.constants import pr_tz
from typing import List, Dict


@dataclass
class DeveloperMetrics:
    tasksBySprint: List[int] = field(default_factory=list)
    pointsClosed: float = 0
    percentContribution: float = 0  # pointsClosed / (totalPoints) * %100
    expectedGrade: float = 0  # floor((pointsClosed / trimmedMean) * %100 , %100)
    lectureTopicTasksClosed: int = 0


@dataclass
class MilestoneData:
    sprints: int = 2
    totalPointsClosed: float = 0
    startDate: datetime = datetime.now(tz=pr_tz)
    endDate: datetime = datetime.now(tz=pr_tz)
    devMetrics: Dict[str, DeveloperMetrics] = field(default_factory=dict)


@dataclass
class LectureTopicTaskData:
    totalLectureTopicTasks: int = 0
    lectureTopicTasksByDeveloper: Dict[str, int] = field(default_factory=dict)
