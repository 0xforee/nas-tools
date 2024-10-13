from datetime import datetime

class TimeUtils:
    @staticmethod
    def time_difference(last_seen_str):
        # 将时间字符串解析为 datetime 对象
        last_seen = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()

        # 计算时间差
        time_diff = current_time - last_seen

        # 获取天、小时和分钟
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # 构建返回结果
        result_parts = []
        if days > 0:
            result_parts.append(f"{days}天")
        if hours > 0:
            result_parts.append(f"{hours}时")
        if minutes > 0 or (days == 0 and hours == 0):  # 如果天和小时都为0，仍然显示分钟
            result_parts.append(f"{minutes}分")

        return ''.join(result_parts) + "前"
