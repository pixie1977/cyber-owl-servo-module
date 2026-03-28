from fastapi import APIRouter, HTTPException
from typing import Optional, Annotated
from pydantic import BaseModel, field_validator, Field

from app.core.low_level_controllers.servo_controller_manager import get_servo_controller


class SetPositionsRequest(BaseModel):
    """
    Модель для установки позиций сервоприводов.
    Все поля необязательные, значения в диапазоне 0–100 (кроме wait).
    """
    hv: Optional[Annotated[int, Field(ge=0, le=100, description="Положение головы по вертикали (0–100)")]] = None
    hh: Optional[Annotated[int, Field(ge=0, le=100, description="Положение головы по горизонтали (0–100)")]] = None
    lw: Optional[Annotated[int, Field(ge=0, le=100, description="Положение левого крыла (0–100)")]] = None
    rw: Optional[Annotated[int, Field(ge=0, le=100, description="Положение правого крыла (0–100)")]] = None
    wait: Optional[Annotated[int, Field(ge=0, description="Задержка после выполнения команды (мс)")]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "hv": 30,
                    "hh": 55,
                    "lw": 100,
                    "rw": 95,
                    "wait": 500
                }
            ]
        }
    }

    @field_validator('*', mode='before')
    def empty_str_to_none(cls, v):
        """Преобразует пустые строки и строковые 'null' в None."""
        if isinstance(v, str) and v.strip() in ('', 'null'):
            return None
        return v


router = APIRouter(prefix="/servo", tags=["servo"])


@router.post("/happy")
async def do_happy():
    """
    Устанавливает радостную позу: голова приподнята, крылья подняты.
    """
    try:
        ctrl = get_servo_controller()
        ctrl.sowa_happy()
        return {"status": "ok", "action": "sowa_happy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка управления сервами: {str(e)}")


@router.post("/sleep")
async def do_sleep():
    """
    Устанавливает позу сна: голова опущена, крылья опущены.
    """
    try:
        ctrl = get_servo_controller()
        ctrl.sowa_sleep()
        return {"status": "ok", "action": "sowa_sleep"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка управления сервами: {str(e)}")


@router.post("/ready")
async def do_ready():
    """
    Устанавливает позу готовности: голова приподнята, правое крыло поднято.
    """
    try:
        ctrl = get_servo_controller()
        ctrl.sowa_ready()
        return {"status": "ok", "action": "sowa_ready"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка управления сервами: {str(e)}")


@router.post("/lw_sign")
async def do_lw_sign(count: Annotated[int, Field(ge=1, le=10)] = 3):
    """
    Махание левым крылом N раз.

    :param count: Количество махов (от 1 до 10)
    """
    ctrl = get_servo_controller()
    ctrl.sowa_lw_sign(count=count)
    return {"status": "ok", "action": "sowa_lw_sign", "count": count}


@router.post("/rw_sign")
async def do_rw_sign(count: Annotated[int, Field(ge=1, le=10)] = 3):
    """
    Махание правым крылом N раз.

    :param count: Количество махов (от 1 до 10)
    """
    ctrl = get_servo_controller()
    ctrl.sowa_rw_sign(count=count)
    return {"status": "ok", "action": "sowa_rw_sign", "count": count}


@router.post("/set_positions")
async def set_positions(request: SetPositionsRequest):
    """
    Установить положения всех сервоприводов через JSON с валидацией.

    Пример тела запроса:
    {
        "hv": 30,
        "hh": 55,
        "lw": 100,
        "rw": 95,
        "wait": 500
    }

    Поля необязательные. `wait` — задержка в миллисекундах.
    """
    ctrl = get_servo_controller()
    commands = []

    # Установка позиций
    if request.hv is not None:
        ctrl.set_head_vertical(request.hv)

    if request.hh is not None:
        ctrl.set_head_horizontal(request.hh)

    if request.lw is not None:
        ctrl.set_left_wing(request.lw)

    if request.rw is not None:
        ctrl.set_right_wing(request.rw)

    # Задержка
    if request.wait is not None:
        commands.append({"id": "wait", "value": request.wait})

    # Отправляем команды в очередь
    for cmd in commands:
        ctrl.add_command(cmd)

    return {
        "status": "ok",
        "set_positions": request.model_dump(exclude_unset=True, exclude_none=True)
    }


@router.get("/stats")
async def get_stats():
    """
    Возвращает статистику подключения к Modbus-устройству.
    """
    try:
        ctrl = get_servo_controller()
        return ctrl.get_connection_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить статистику: {str(e)}")