"""Drive the refund workflow through a real Edge DOM using Selenium."""
from __future__ import annotations

import argparse
import json
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options

from agents import safe_recovery_policy


def run(url: str) -> dict:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    try:
        driver = webdriver.Edge(options=options)
    except WebDriverException as exc:
        raise RuntimeError(
            "无法启动 Edge WebDriver；请安装与 Edge 匹配的 msedgedriver，或设置 Selenium Manager 可访问驱动下载地址。"
        ) from exc
    trace = []
    retries: dict[str, int] = {}
    try:
        driver.get(url)
        for _ in range(20):
            time.sleep(0.05)
            state = json.loads(driver.find_element(By.ID, "state-json").text)
            state["events"] = state.get("events", [])
            action = safe_recovery_policy(state, retries)
            driver.find_element(By.CSS_SELECTOR, f"button[data-action='{action}']").click()
            time.sleep(0.05)
            trace.append({"action": action, "status": driver.find_element(By.ID, "status").text})
            state = json.loads(driver.find_element(By.ID, "state-json").text)
            if state["status"] in {"submitted", "human_handoff", "failed"}:
                break
        final = json.loads(driver.find_element(By.ID, "state-json").text)
        return {"trace": trace, "final": final}
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/")
    args = parser.parse_args()
    print(json.dumps(run(args.url), indent=2))


if __name__ == "__main__":
    main()
