from jinja2 import Template

PLANNER_AGENT_PROMPT = """
你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

**输出格式:**
严格按照以下JSON格式返回:
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "location": "成都",
      "latitude": 39.916527,
      "longitude": 116.397128,
      "timezone": "Asia/Shanghai",
      "start_date": "2025-01-25",
      "end_date": "2025-01-30",
      "daily_weather": [
        {
          "date": "2025-01-25",
          "weather_desc": "晴",
          "weather_code": 800,
          "temperature": 25,
          "night_temp": 15,
          "wind_direction": "南风",
          "wind_power": "1-3级"
        }
      ]
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
"""


PLANNER_QUERY_PROMPT = Template(
    """
请根据以下信息生成{{city}}的{{travel_days}}天旅行计划:

**基本信息:**
- 城市: {{city}}
- 日期: {{start_date}} 至 {{end_date}}
- 天数: {{travel_days}}天
- 交通方式: {{transportation}}
- 住宿: {{accommodation}}
- 偏好: {{preferences}}

**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**用户额外要求:**
{{free_text_input}}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
3. 考虑景点之间的距离和交通方式
4. 返回完整的JSON格式数据
5. 景点的经纬度坐标要真实准确
"""
)
