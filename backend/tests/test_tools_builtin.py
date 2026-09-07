"""Tests for built-in safe starter tools: calculator, datetime, and system_info."""

import pytest
from app.tools.builtin.calculator import CalculatorTool, SafeMathEvaluator
from app.tools.builtin.datetime import DateTimeTool
from app.tools.builtin.system_info import SystemInfoTool


# ==========================================
# Calculator Tests
# ==========================================

@pytest.mark.asyncio
async def test_calculator_arithmetic_operations() -> None:
    """Ensure standard arithmetic expressions evaluate accurately."""
    calc = CalculatorTool()

    assert await calc.execute("2 + 2") == 4
    assert await calc.execute("10 - 4.5") == 5.5
    assert await calc.execute("3 * 7") == 21
    assert await calc.execute("20 / 4") == 5.0
    assert await calc.execute("10 % 3") == 1
    assert await calc.execute("2 ** 8") == 256
    assert await calc.execute("(10 * 5) / 2") == 25.0
    assert await calc.execute("-5 + 10") == 5


@pytest.mark.asyncio
async def test_calculator_division_by_zero() -> None:
    """Ensure division by zero raises clean ValueError."""
    calc = CalculatorTool()
    with pytest.raises(ValueError) as exc:
        await calc.execute("10 / 0")
    assert "Division by zero" in str(exc.value)


@pytest.mark.asyncio
async def test_calculator_malicious_expressions_rejected() -> None:
    """Ensure dangerous AST nodes and code execution attempts are strictly blocked."""
    calc = CalculatorTool()

    malicious_inputs = [
        "__import__('os').system('dir')",
        "eval('2 + 2')",
        "exec('print(1)')",
        "open('README.md').read()",
        "os.environ",
        "lambda x: x",
        "[x for x in range(10)]",
        "x + 1",
        "print('hello')",
        "(lambda: 1)()",
        "__builtins__",
        "getattr(math, 'sin')(1)",
        "2 ** 1000000",  # Exponentiation DoS attempt
    ]

    for malicious in malicious_inputs:
        with pytest.raises(ValueError):
            await calc.execute(malicious)


def test_calculator_verify() -> None:
    """Ensure verify hook rejects invalid/infinite numbers."""
    calc = CalculatorTool()
    assert calc.verify(42) is True
    assert calc.verify(3.14) is True
    assert calc.verify(float("nan")) is False
    assert calc.verify(float("inf")) is False
    assert calc.verify("not_a_number") is False


# ==========================================
# Datetime Tests
# ==========================================

@pytest.mark.asyncio
async def test_datetime_utc_and_timezones() -> None:
    """Ensure datetime tool handles UTC and specified IANA timezones."""
    dt_tool = DateTimeTool()

    # Default UTC
    res_utc = await dt_tool.execute()
    assert res_utc["timezone"] == "UTC"
    assert "T" in res_utc["iso"]
    assert dt_tool.verify(res_utc) is True

    # Asia/Kolkata
    res_kolkata = await dt_tool.execute(timezone="Asia/Kolkata")
    assert res_kolkata["timezone"] == "Asia/Kolkata"
    assert "date" in res_kolkata
    assert "time" in res_kolkata
    assert "day_of_week" in res_kolkata

    # America/New_York
    res_ny = await dt_tool.execute(timezone="America/New_York")
    assert res_ny["timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_datetime_invalid_timezone() -> None:
    """Ensure invalid timezone raises clean ValueError."""
    dt_tool = DateTimeTool()
    with pytest.raises(ValueError) as exc:
        await dt_tool.execute(timezone="Mars/Olympus_Mons")
    assert "Invalid or unrecognized IANA timezone" in str(exc.value)


# ==========================================
# System Info Tests
# ==========================================

@pytest.mark.asyncio
async def test_system_info_safe_metadata() -> None:
    """Ensure system_info returns safe fields without leaking environment or secrets."""
    sys_tool = SystemInfoTool()
    info = await sys_tool.execute()

    assert "os" in info
    assert "os_release" in info
    assert "architecture" in info
    assert "python_version" in info

    assert sys_tool.verify(info) is True

    # Ensure no environment variables or secret keywords exist
    for key, value in info.items():
        assert "key" not in key.lower()
        assert "token" not in key.lower()
        assert "secret" not in key.lower()
        assert "pass" not in key.lower()
