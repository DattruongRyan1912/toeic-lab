#!/usr/bin/env python3
"""
Update docs/index.html with:
1. 60 Cleaned Flashcards in FLASHCARDS array.
2. Full 30 Part 5 Questions (Q101 -> Q130) with 3D Explanations in PART5_QUESTIONS array.
3. Mini-Test Module View (#view-minitest) with Timer, Jump Pills, Real-time Scoring and 1-click RCA Error Log saving.
4. Sidebar navigation item for Mini-Test Part 5.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "docs" / "index.html"

# Load dumped data
with open(BASE_DIR / "scratch" / "all_flashcards.json", "r", encoding="utf-8") as f:
    flashcards_data = json.load(f)

with open(BASE_DIR / "scratch" / "part5_questions.json", "r", encoding="utf-8") as f:
    part5_data = json.load(f)

with open(BASE_DIR / "scratch" / "minitest.js", "r", encoding="utf-8") as f:
    minitest_js_template = f.read()

with open(INDEX_HTML, "r", encoding="utf-8") as f:
    html = f.read()

# -------------------------------------------------------------
# 1. Update CSS with Mini-Test Styles
# -------------------------------------------------------------
test_css = """
    /* Mini-Test Part 5 Styles */
    .test-timer-badge {
      font-family: var(--font-mono);
      font-size: 15px;
      font-weight: 800;
      color: var(--accent);
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .test-jump-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 14px 0 20px;
    }
    .test-jump-pill {
      width: 34px;
      height: 32px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-muted);
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }
    .test-jump-pill:hover {
      border-color: var(--accent);
      color: var(--text-main);
    }
    .test-jump-pill.answered {
      background: var(--accent-glow);
      border-color: var(--accent);
      color: var(--accent);
    }
    .test-jump-pill.correct {
      background: rgba(52, 211, 153, 0.2) !important;
      border-color: var(--accent-green) !important;
      color: var(--accent-green) !important;
    }
    .test-jump-pill.incorrect {
      background: rgba(251, 113, 133, 0.2) !important;
      border-color: var(--accent-rose) !important;
      color: var(--accent-rose) !important;
    }
    .test-question-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      transition: border-color 0.2s ease;
    }
    .test-choices-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
      margin: 14px 0;
    }
    .test-choice-btn {
      padding: 12px 14px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      color: var(--text-main);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 10px;
      text-align: left;
      transition: all 0.15s ease;
    }
    .test-choice-btn:hover {
      border-color: var(--accent);
      background: var(--bg-secondary);
    }
    .test-choice-btn.selected {
      border-color: var(--accent);
      background: var(--accent-glow);
      color: var(--accent);
      font-weight: 700;
    }
    .test-choice-btn.is-correct {
      border-color: var(--accent-green) !important;
      background: rgba(52, 211, 153, 0.15) !important;
      color: var(--accent-green) !important;
      font-weight: 700 !important;
    }
    .test-choice-btn.is-incorrect {
      border-color: var(--accent-rose) !important;
      background: rgba(251, 113, 133, 0.15) !important;
      color: var(--accent-rose) !important;
      font-weight: 700 !important;
    }
    .test-choice-letter {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 800;
      flex-shrink: 0;
    }
    .test-analysis-box {
      margin-top: 14px;
      padding: 16px;
      background: var(--bg-primary);
      border-radius: 8px;
      border-left: 4px solid var(--accent);
      font-size: 13px;
      line-height: 1.6;
      display: none;
    }
    .test-analysis-box.show {
      display: block;
    }
"""

if ".test-timer-badge" not in html:
    html = html.replace("/* Lesson Selector Pills */", test_css + "\n    /* Lesson Selector Pills */")

# -------------------------------------------------------------
# 2. Update Sidebar Navigation
# -------------------------------------------------------------
minitest_nav = """      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('flashcards')" data-module="flashcards" class="active">🗂️ Flashcard SRS Web</a></li>
      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('minitest')" data-module="minitest" style="color: var(--accent); font-weight: 700;">🎯 Thi thử Part 5 (ETS 2024)</a></li>"""

if "data-module=\"minitest\"" not in html:
    html = html.replace(
        """      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('flashcards')" data-module="flashcards" class="active">🗂️ Flashcard SRS Web</a></li>""",
        minitest_nav
    )

# -------------------------------------------------------------
# 3. Add Mini-Test View Panel (#view-minitest)
# -------------------------------------------------------------
minitest_view = """
  <!-- ============================================================== -->
  <!-- VIEW: THI THỬ PART 5 (ETS 2024 TEST 01 - 30 CÂU THỰC CHIẾN)    -->
  <!-- ============================================================== -->
  <div id="view-minitest" class="view-panel">
    <div class="section-header">
      <h2 class="section-title">🎯 Đề Thi Thử Part 5: ETS TOEIC 2024 Test 01</h2>
      <span class="section-tag">REAL EXAM SIMULATION (Q101 - Q130)</span>
    </div>

    <!-- Test Control Header Bar -->
    <div class="card" style="padding: 20px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div>
          <div style="font-size: 16px; font-weight: 800; display: flex; align-items: center; gap: 8px;">
            <span>⏱️ Thời gian tiêu chuẩn:</span>
            <span class="test-timer-badge" id="testTimerBadge">12:00</span>
            <button type="button" id="btnToggleTimer" onclick="toggleTestTimer()" style="padding: 5px 10px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-main); border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">
              Tạm Dừng ⏸️
            </button>
          </div>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
            Mục tiêu Part 5: Giải 30 câu trong 10 - 12 phút (20 - 24 giây/câu), đạt độ chính xác > 24/30 để hướng tới TOEIC 800+.
          </p>
        </div>

        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
          <div style="font-size: 13px; font-weight: 700; color: var(--text-muted);">
            Tiến độ: <span id="testAnsweredCount" style="color: var(--accent); font-weight: 800;">0</span> / 30 câu
          </div>
          <button type="button" onclick="submitPart5Test()" id="btnSubmitTest" style="padding: 10px 18px; background: var(--accent); color: #fff; border: none; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span>📝</span> Chấm Điểm & Phân Tích
          </button>
          <button type="button" onclick="resetPart5Test()" style="padding: 10px 14px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-main); border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer;">
            🔄 Làm Lại
          </button>
        </div>
      </div>

      <!-- Jump Pills Bar -->
      <div style="border-top: 1px solid var(--border-color); margin-top: 16px; padding-top: 14px;">
        <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">
          Bảng Chọn Câu Hỏi Nhanh (Click để nhảy tới câu):
        </div>
        <div class="test-jump-pills" id="testJumpPillsContainer">
          <!-- Rendered via JS -->
        </div>
      </div>

      <!-- Test Score Summary Banner (Hidden until submitted) -->
      <div id="testResultBanner" style="display: none; margin-top: 16px; padding: 16px 20px; background: var(--bg-primary); border: 1px solid var(--accent-green); border-radius: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color: var(--accent-green); text-transform: uppercase;">
              🎉 KẾT QUẢ BÀI THI THỬ PART 5
            </div>
            <div style="font-size: 24px; font-weight: 800; margin-top: 4px;">
              Điểm số: <span id="testScoreVal" style="color: var(--accent);">0</span> / 30 câu đúng (<span id="testScorePercent">0%</span>)
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;" id="testScoreFeedback">
              <!-- Evaluation note -->
            </div>
          </div>
          <div>
            <span class="badge-pill" id="testCefrBadge" style="background: rgba(52, 211, 153, 0.15); color: var(--accent-green); border-color: rgba(52, 211, 153, 0.3); font-size: 13px; padding: 6px 14px;">
              B2 - Working Proficiency
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 30 Test Questions Container -->
    <div id="testQuestionsListContainer">
      <!-- Rendered dynamically via JS -->
    </div>
  </div>
"""

if 'id="view-minitest"' not in html:
    html = html.replace(
        '  <!-- ============================================================== -->\n  <!-- VIEW 2: 12 CHUYÊN ĐỀ CÚ PHÁP PART 5 (LESSONS MODULE)          -->',
        minitest_view + '\n  <!-- ============================================================== -->\n  <!-- VIEW 2: 12 CHUYÊN ĐỀ CÚ PHÁP PART 5 (LESSONS MODULE)          -->'
    )

# -------------------------------------------------------------
# 4. Update validModules in navigateToModule()
# -------------------------------------------------------------
html = html.replace(
    "const validModules = ['flashcards', 'lessons', 'error-log', 'calculator', 'roadmaps', 'settings', 'reference'];",
    "const validModules = ['flashcards', 'minitest', 'lessons', 'error-log', 'calculator', 'roadmaps', 'settings', 'reference'];"
)

# -------------------------------------------------------------
# 5. Replace FLASHCARDS array with full 60 cards
# -------------------------------------------------------------
flashcards_json_str = json.dumps(flashcards_data, ensure_ascii=False, indent=6)
start_idx = html.find("const FLASHCARDS = [")
end_idx = html.find("let currentCardIndex = 0;")
if start_idx != -1 and end_idx != -1:
    html = html[:start_idx] + f"const FLASHCARDS = {flashcards_json_str};\n\n    " + html[end_idx:]

# -------------------------------------------------------------
# 6. Add PART5_QUESTIONS array and Mini-Test JavaScript Logic
# -------------------------------------------------------------
part5_json_str = json.dumps(part5_data, ensure_ascii=False, indent=4)
minitest_js = minitest_js_template.replace("__PART5_QUESTIONS_PLACEHOLDER__", part5_json_str)

# Insert JS before renderCurrentCard()
if "const PART5_QUESTIONS =" not in html:
    html = html.replace(
        "    renderCurrentCard();",
        minitest_js + "\n    renderPart5Test();\n    renderCurrentCard();"
    )

with open(INDEX_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print("Successfully updated docs/index.html with 60 Flashcards and 30 Part 5 Questions!")
