from datetime import datetime

class TimeUtils:
    @staticmethod
    def time_difference(last_seen_str):

        try:
            if not last_seen_str:
                return ""
            if not isinstance(last_seen_str, str):
                return ""
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
        except:
            return ''

    @staticmethod
    def less_than_days(date_str, target_days):
        """
        小于三十天
        """
        try:
            if not date_str:
                return False
            if not isinstance(date_str, str):
                return False
            # 将时间字符串解析为 datetime 对象
            last_seen = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()

            # 计算时间差
            time_diff = current_time - last_seen

            # 获取天、小时和分钟
            days = time_diff.days

            if days > target_days:
                return False
            else:
                return True
        except:
            return False

