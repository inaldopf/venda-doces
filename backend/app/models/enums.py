import enum


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PAID = "PAID"
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    PIX = "PIX"
    CARD = "CARD"
    OTHER = "OTHER"
