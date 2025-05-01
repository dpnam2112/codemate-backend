# metrics.py

class MetricsCalculator:
    def __init__(self):
        self.total = 0
        self.pass_count = 0
        self.fail_count = 0
        self.runtime_error_count = 0
        self.timeout_count = 0

    def update(self, outcome: str):
        self.total += 1
        if outcome == "Pass":
            self.pass_count += 1
        elif outcome == "Fail":
            self.fail_count += 1
        elif outcome == "Runtime Error":
            self.runtime_error_count += 1
        elif outcome == "Timeout":
            self.timeout_count += 1

    def print_summary(self):
        print("\n--- Validation Summary ---")
        if self.total == 0:
            print("No testcases evaluated.")
            return

        print(f"Total testcases: {self.total}")
        print(f"Pass: {self.pass_count} ({self.pass_count/self.total:.2%})")
        print(f"Fail: {self.fail_count} ({self.fail_count/self.total:.2%})")
        print(f"Runtime Errors: {self.runtime_error_count} ({self.runtime_error_count/self.total:.2%})")
        print(f"Timeouts: {self.timeout_count} ({self.timeout_count/self.total:.2%})")

