#!/usr/bin/env python3
"""
Build complete, clean, modular frontend docs/index.html with:
1. Baseline clean foundation from scratch/index_baseline.html.
2. Full 60 Core Vocab Flashcards pre-rendered directly into HTML (Server-Side Pre-rendered)
   ensuring the table is NEVER EMPTY even before JavaScript executes or if scripts are delayed!
3. Pre-populated category filter options for instant filtering.
4. Full 30 Part 5 Questions (Q101 -> Q130) with 3D RCA in PART5_QUESTIONS array.
5. Mini-Test Module View (#view-minitest) with Timer, Jump Pills, 3D Review, and 1-Click Error Log.
6. Vocabulary Notebook & Self-Study Hub (#view-vocab-hub) with:
   - Vocab Vault table with Instant Search, Category Filter, Audio Speech, and Paraphrase pairs.
   - Quick Add Vocab Modal with AI DeepSeek Auto-Fill.
   - Self-Study Drills: 4-Choice Quick Quiz & Typing/Fill-in-the-blank challenge (No Anki needed!).
7. Sidebar navigation linking all modules.
"""

import json
import html as html_lib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "scratch" / "index_baseline.html", "r", encoding="utf-8") as f:
    html = f.read()

with open(BASE_DIR / "scratch" / "all_flashcards.json", "r", encoding="utf-8") as f:
    flashcards_data = json.load(f)

with open(BASE_DIR / "scratch" / "part5_questions.json", "r", encoding="utf-8") as f:
    part5_data = json.load(f)

with open(BASE_DIR / "scratch" / "minitest.js", "r", encoding="utf-8") as f:
    minitest_js_template = f.read()

with open(BASE_DIR / "scratch" / "vocab_hub.html", "r", encoding="utf-8") as f:
    vocab_hub_html = f.read()

with open(BASE_DIR / "scratch" / "vocab_hub.js", "r", encoding="utf-8") as f:
    vocab_hub_js = f.read()

# -------------------------------------------------------------
# 1. Pre-render 60 Vocab Rows directly into HTML table (SSR)
# -------------------------------------------------------------
def generate_static_vocab_rows(cards):
    rows = []
    for card in cards:
        word = html_lib.escape(card.get("word", ""))
        ipa = html_lib.escape(card.get("ipa", ""))
        w_type = html_lib.escape(card.get("type", "v"))
        cat = html_lib.escape(card.get("cat", "General Business"))
        meaning = html_lib.escape(card.get("meaning", ""))
        colloc = html_lib.escape(card.get("collocations", "---"))
        para = html_lib.escape(card.get("paraphrase", "---"))
        front = card.get("front", "")
        full = card.get("fullSentence", "")
        display = front if ("______" in front) else (full or front)
        display = html_lib.escape(display)
        cid = card.get("id", 1)

        row = f"""            <tr style="border-bottom: 1px solid var(--border-color); transition: background 0.15s;" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='transparent'">
              <td style="padding: 12px 16px; vertical-align: top;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-weight: 700; font-size: 15px; color: var(--accent);">{word}</span>
                  <button onclick="playVocabWord('{word}')" title="Nghe phát âm US" style="background: none; border: none; cursor: pointer; font-size: 15px; padding: 2px; color: var(--text-muted); transition: color 0.15s;" onmouseover="this.style.color='var(--accent)'" onmouseout="this.style.color='var(--text-muted)'">
                    🔊
                  </button>
                </div>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                  /{ipa}/ <span style="color: var(--accent-purple); font-weight: 600;">({w_type})</span>
                </div>
              </td>
              <td style="padding: 12px 16px; vertical-align: top;">
                <span class="badge-error badge-vocab" style="font-size: 10px; padding: 2px 6px;">{cat}</span>
              </td>
              <td style="padding: 12px 16px; vertical-align: top; font-weight: 500; color: var(--text-main);">
                {meaning}
              </td>
              <td style="padding: 12px 16px; vertical-align: top; font-size: 12px; color: var(--text-muted); line-height: 1.4;">
                {colloc}
              </td>
              <td style="padding: 12px 16px; vertical-align: top; font-size: 12px; color: var(--accent-amber); font-weight: 500;">
                {para}
              </td>
              <td style="padding: 12px 16px; vertical-align: top; font-size: 12px; color: var(--text-muted); font-style: italic; line-height: 1.4;">
                "{display}"
              </td>
              <td style="padding: 12px 16px; vertical-align: top; text-align: center;">
                <div style="display: flex; gap: 6px; justify-content: center; align-items: center;">
                  <button onclick="toggleVocabMastered({cid})" title="Đánh dấu đã thuộc" style="padding: 4px 8px; border-radius: 6px; font-size: 11px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-muted); cursor: pointer;">
                    ⭐ Ôn
                  </button>
                  <button onclick="askDeepSeekAboutVocab('{word}')" title="Hỏi AI DeepSeek về sắc thái từ này" style="padding: 4px 6px; border-radius: 6px; font-size: 11px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--accent-purple); cursor: pointer;">
                    🤖
                  </button>
                  <button onclick="deleteVocabCard({cid})" title="Xóa từ khỏi sổ tay" style="padding: 4px 6px; border-radius: 6px; font-size: 11px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--accent-rose); cursor: pointer;">
                    🗑️
                  </button>
                </div>
              </td>
            </tr>"""
        rows.append(row)
    return "\n".join(rows)

static_rows_html = generate_static_vocab_rows(flashcards_data)

# Pre-populate categories in select
unique_cats = sorted(list(set(c.get("cat", "General Business") for c in flashcards_data if c.get("cat"))))
cat_options = '<option value="all">Tất cả chủ đề</option>\n' + "\n".join(
    f'            <option value="{html_lib.escape(c)}">{html_lib.escape(c)}</option>' for c in unique_cats
)

# Inject pre-rendered rows into vocab_hub_html
vocab_hub_html = vocab_hub_html.replace(
    '<tbody id="vocabTableBody">\n            <!-- Dynamically populated via renderVocabTable() -->\n          </tbody>',
    f'<tbody id="vocabTableBody">\n{static_rows_html}\n          </tbody>'
)
vocab_hub_html = vocab_hub_html.replace(
    '<strong id="vocabDisplayedCount" style="color: var(--accent); font-weight: 700;">0</strong>',
    f'<strong id="vocabDisplayedCount" style="color: var(--accent); font-weight: 700;">{len(flashcards_data)}</strong>'
)
vocab_hub_html = vocab_hub_html.replace(
    '<option value="all">Tất cả chủ đề</option>',
    cat_options
)

# -------------------------------------------------------------
# 2. Add CSS for Mini-Test and Vocab Hub
# -------------------------------------------------------------
extra_css = """
    /* Unified Modern Button System (Dark Theme First) */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
      border: 1px solid transparent;
      text-decoration: none;
      outline: none;
    }
    .btn-primary {
      background: var(--accent);
      color: #0b132b !important;
      border-color: var(--accent);
    }
    .btn-primary:hover {
      filter: brightness(1.1);
      box-shadow: 0 0 14px var(--accent-glow);
    }
    .btn-accent-glow {
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(14, 165, 233, 0.25) 100%);
      border: 1px solid var(--accent) !important;
      color: var(--accent) !important;
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.1);
    }
    .btn-accent-glow:hover {
      background: var(--accent) !important;
      color: #0b132b !important;
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.35);
    }
    .btn-outline {
      background: var(--bg-card) !important;
      border: 1px solid var(--border-color) !important;
      color: var(--text-main) !important;
    }
    .btn-outline:hover {
      background: var(--bg-hover) !important;
      border-color: var(--text-muted) !important;
      color: #ffffff !important;
    }

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

html = html.replace("/* Lesson Selector Pills */", extra_css + "\n    /* Lesson Selector Pills */")

# -------------------------------------------------------------
# 3. Update Sidebar Navigation
# -------------------------------------------------------------
old_nav = """      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('flashcards')" data-module="flashcards" class="active">🗂️ Flashcard SRS Web</a></li>"""

new_nav = """      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('flashcards')" data-module="flashcards" class="active">🗂️ Flashcard SRS Web</a></li>
      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('vocab-hub')" data-module="vocab-hub" style="color: var(--accent-green); font-weight: 700;">📖 Sổ tay Từ vựng</a></li>
      <li class="nav-item"><a href="javascript:void(0)" onclick="navigateToModule('minitest')" data-module="minitest" style="color: var(--accent); font-weight: 700;">🎯 Thi thử Part 5 (ETS 2024)</a></li>"""

html = html.replace(old_nav, new_nav)

# -------------------------------------------------------------
# 4. Update navigateToModule and validMods
# -------------------------------------------------------------
old_nav_fn = """    function navigateToModule(moduleId) {
      const validModules = ['flashcards', 'lessons', 'error-log', 'calculator', 'roadmaps', 'settings', 'reference'];
      if (!validModules.includes(moduleId)) {
        moduleId = 'flashcards';
      }

      // Hide all panels
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active-view'));

      // Show target panel
      const target = document.getElementById('view-' + moduleId);
      if (target) {
        target.classList.add('active-view');
      }"""

new_nav_fn = """    function navigateToModule(moduleId) {
      const validModules = ['flashcards', 'vocab-hub', 'minitest', 'lessons', 'error-log', 'calculator', 'roadmaps', 'settings', 'reference'];
      if (!validModules.includes(moduleId)) {
        moduleId = 'flashcards';
      }

      // Hide all panels
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active-view'));

      // Show target panel
      const target = document.getElementById('view-' + moduleId);
      if (target) {
        target.classList.add('active-view');
      }

      if (moduleId === 'vocab-hub' && typeof renderVocabTable === 'function') {
        renderVocabTable();
      }"""

html = html.replace(old_nav_fn, new_nav_fn)

# Also update validMods at bottom init
html = html.replace(
    "const validMods = ['flashcards', 'lessons', 'error-log', 'calculator', 'roadmaps', 'settings', 'reference'];",
    "const validMods = ['flashcards', 'vocab-hub', 'minitest', 'lessons', 'error-log', 'calculator', 'roadmaps', 'settings', 'reference'];"
)

# -------------------------------------------------------------
# 5. Update count badges in Flashcards view (from 20 to 60)
# -------------------------------------------------------------
html = html.replace("0 / 20 từ", f"0 / {len(flashcards_data)} từ")
html = html.replace("Thẻ 1 / 20", f"Thẻ 1 / {len(flashcards_data)}")
html = html.replace("Tất cả (20)", f"Tất cả ({len(flashcards_data)})")

# -------------------------------------------------------------
# 6. Insert View Panels: view-vocab-hub and view-minitest
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

    <!-- Questions Container List -->
    <div id="testQuestionsList">
      <!-- 30 Questions rendered dynamically via JS -->
    </div>
  </div>
"""

panels_to_insert = "\n" + vocab_hub_html + "\n" + minitest_view + "\n"
html = html.replace('<div id="view-lessons" class="view-panel">', panels_to_insert + '  <div id="view-lessons" class="view-panel">')

# -------------------------------------------------------------
# 7. Replace FLASHCARDS array with 60 words (using `let` for mutability)
# -------------------------------------------------------------
fc_start = html.find("const FLASHCARDS = [")
fc_end = html.find("let currentCardIndex = 0;", fc_start)
if fc_start != -1 and fc_end != -1:
    new_flashcards_js = "let FLASHCARDS = " + json.dumps(flashcards_data, ensure_ascii=False, indent=2) + ";\n\n    "
    html = html[:fc_start] + new_flashcards_js + html[fc_end:]
else:
    print("WARNING: Could not find FLASHCARDS array boundaries!")

# -------------------------------------------------------------
# 8. Append Mini-Test and Vocab Hub JS before closing </script>
# -------------------------------------------------------------
minitest_js_final = minitest_js_template.replace("__PART5_QUESTIONS_PLACEHOLDER__", json.dumps(part5_data, ensure_ascii=False, indent=4))

# Also ensure syncFlashcardsFromDb triggers renderVocabTable
html = html.replace(
    "FLASHCARDS.splice(0, FLASHCARDS.length, ...mapped);\n              renderCurrentCard();",
    "FLASHCARDS.splice(0, FLASHCARDS.length, ...mapped);\n              renderCurrentCard();\n              if (typeof renderVocabTable === 'function') renderVocabTable();"
)

js_bundle = f"""
    // ==============================================================
    // PART 5 BENCHMARK TEST (ETS 2024 TEST 01: Q101 - Q130)
    // ==============================================================
    {minitest_js_final}

    // ==============================================================
    // VOCABULARY NOTEBOOK & SELF-STUDY HUB LOGIC
    // ==============================================================
    {vocab_hub_js}

    // Auto-init on page load
    try {{
      if (typeof renderPart5Test === 'function') renderPart5Test();
      if (typeof renderVocabTable === 'function') renderVocabTable();
    }} catch (err) {{
      console.warn("Auto-init warning:", err);
    }}
"""

script_close_tag = "</script>"
last_script_idx = html.rfind(script_close_tag)
if last_script_idx != -1:
    html = html[:last_script_idx] + js_bundle + "\n  " + html[last_script_idx:]
else:
    print("WARNING: Could not find </script> tag!")

# Write output to docs/index.html
with open(BASE_DIR / "docs" / "index.html", "w", encoding="utf-8") as f:
    f.write(html)

# Also copy to docs/toeic_study_guide.html
with open(BASE_DIR / "docs" / "toeic_study_guide.html", "w", encoding="utf-8") as f:
    f.write(html)

print("SUCCESS: Rebuilt docs/index.html with pre-rendered vocab table and clean JS!")
print(f"Total lines: {len(html.splitlines())}")
