from __future__ import annotations

DEFAULT_JUDGE0_BASE_URL = "https://ce.judge0.com"
CODING_ROUND_DURATION_MINUTES = 15
CODING_ROUND_MAX_ATTEMPTS = 5
CODEFORCES_MIN_RATING = 1200
CODEFORCES_MAX_RATING = 1500
DEFAULT_CODE_LANGUAGE = "python"
REQUEST_USER_AGENT = "TalentScout Coding Round/1.0"


LANGUAGE_PRESETS: dict[str, dict[str, object]] = {
    "python": {
        "label": "Python 3.11",
        "judge0_language_id": 92,
        "starter_code": """import sys


def solve() -> None:
    data = sys.stdin.read().strip().split()
    # TODO: implement the solution.
    _ = data


if __name__ == "__main__":
    solve()
""",
    },
    "cpp": {
        "label": "C++17",
        "judge0_language_id": 105,
        "starter_code": """#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // TODO: implement the solution.

    return 0;
}
""",
    },
    "java": {
        "label": "Java 17",
        "judge0_language_id": 91,
        "starter_code": """import java.io.BufferedInputStream;
import java.io.IOException;

public class Main {
    public static void main(String[] args) throws Exception {
        FastScanner fs = new FastScanner();
        String input = fs.readAll();
        // TODO: implement the solution.
        if (input == null) {
            input = "";
        }
    }

    static class FastScanner {
        private final BufferedInputStream in = new BufferedInputStream(System.in);

        String readAll() throws IOException {
            StringBuilder sb = new StringBuilder();
            byte[] buffer = new byte[1 << 12];
            int read;
            while ((read = in.read(buffer)) != -1) {
                sb.append(new String(buffer, 0, read));
            }
            return sb.toString();
        }
    }
}
""",
    },
    "javascript": {
        "label": "JavaScript (Node.js 22)",
        "judge0_language_id": 102,
        "starter_code": """'use strict';

const fs = require('fs');
const input = fs.readFileSync(0, 'utf8');

// TODO: implement the solution.
void input;
""",
    },
}


def get_language_payloads() -> list[dict[str, object]]:
    return [
        {
            "slug": slug,
            "label": str(config["label"]),
            "judge0_language_id": int(config["judge0_language_id"]),
            "starter_code": str(config["starter_code"]),
        }
        for slug, config in LANGUAGE_PRESETS.items()
    ]

