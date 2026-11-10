import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def generate_exam_excel_workbook(
    exam: Dict[str, Any],
    records: List[Dict[str, Any]],
    only_approved: bool = True
) -> Tuple[io.BytesIO, str]:
    """
    Generate an academic-grade formatted Excel workbook using openpyxl.
    Includes metadata banner, question-wise columns, totals, verification statuses,
    summary statistics, and professional cell styling.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet()
    ws.title = f"{exam.get('subject_code', 'EXAM')}_Marks"
    ws.views.sheetView[0].showGridLines = True

    # Palette
    NAVY_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    HEADER_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    META_BG = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    ALT_ROW_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    APPROVED_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    PENDING_FILL = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    FLAG_FILL = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    FOOTER_FILL = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    FONT_TITLE = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    FONT_META_LABEL = Font(name="Calibri", size=10, bold=True, color="475569")
    FONT_META_VAL = Font(name="Calibri", size=10, bold=False, color="0F172A")
    FONT_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    FONT_DATA = Font(name="Calibri", size=10, color="0F172A")
    FONT_BOLD = Font(name="Calibri", size=10, bold=True, color="0F172A")
    FONT_APPROVED = Font(name="Calibri", size=9, bold=True, color="166534")
    FONT_FLAG = Font(name="Calibri", size=9, bold=True, color="991B1B")
    FONT_PENDING = Font(name="Calibri", size=9, bold=True, color="92400E")

    ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
    ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
    ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

    THIN_BORDER_SIDE = Side(border_style="thin", color="CBD5E1")
    CELL_BORDER = Border(
        left=THIN_BORDER_SIDE, right=THIN_BORDER_SIDE,
        top=THIN_BORDER_SIDE, bottom=THIN_BORDER_SIDE
    )

    # 1. Filter records if requested
    if only_approved:
        export_records = [r for r in records if r.get("status") == "APPROVED"]
    else:
        export_records = list(records)

    # Sort by student_id ascending
    export_records.sort(key=lambda r: str(r.get("student_id", "")))

    questions: List[Dict[str, Any]] = exam.get("questions", [])
    total_cols = 3 + len(questions) + 5  # S.No, ID, Name, Questions..., Obtained, Max, %, Status, Approved At
    last_col_letter = get_column_letter(total_cols)

    # 2. Main Title Banner (Row 1)
    ws.merge_cells(f"A1:{last_col_letter}1")
    title_cell = ws["A1"]
    title_cell.value = "SMARTMARKS AI — OFFICIAL EXAMINATION EVALUATION RECORD"
    title_cell.font = FONT_TITLE
    title_cell.fill = NAVY_FILL
    title_cell.alignment = ALIGN_CENTER
    ws.row_dimensions[1].height = 36

    # 3. Examination Metadata Block (Rows 3-5)
    meta_items = [
        ("Subject:", f"{exam.get('subject_code', '')} — {exam.get('subject_name', '')}",
         "Examination Type:", str(exam.get("exam_type", "")).replace("_", " ").title()),
        ("Semester & Academic Year:", f"Semester {exam.get('semester', '')} | Year {exam.get('academic_year', '2025-2026')}",
         "Examination Date:", str(exam.get("exam_date", ""))),
        ("Configured Maximum Marks:", f"{exam.get('total_marks', 0.0)} Marks",
         "Export Generated At:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
    ]

    for row_idx, (k1, v1, k2, v2) in enumerate(meta_items, start=3):
        ws[f"A{row_idx}"].value = k1
        ws[f"A{row_idx}"].font = FONT_META_LABEL
        ws[f"A{row_idx}"].fill = META_BG

        ws[f"B{row_idx}"].value = v1
        ws[f"B{row_idx}"].font = FONT_META_VAL

        ws[f"D{row_idx}"].value = k2
        ws[f"D{row_idx}"].font = FONT_META_LABEL
        ws[f"D{row_idx}"].fill = META_BG

        ws[f"E{row_idx}"].value = v2
        ws[f"E{row_idx}"].font = FONT_META_VAL
        ws.row_dimensions[row_idx].height = 20

    # 4. Table Headers (Row 7)
    header_row = 7
    ws.row_dimensions[header_row].height = 26

    headers = ["S.No", "Student ID / Roll No", "Student Name"]
    for q in questions:
        headers.append(f"{q.get('display_name', q.get('question_id'))} [{q.get('max_marks')}m]")
    headers.extend(["Total Obtained", "Max Marks", "Percentage (%)", "Status", "Approval Stamp"])

    for col_idx, h_text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=h_text)
        cell.font = FONT_HEADER
        cell.fill = HEADER_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = CELL_BORDER

    # 5. Populate Data Rows
    current_row = 8
    scores_for_stats: List[float] = []

    for s_no, record in enumerate(export_records, start=1):
        ws.row_dimensions[current_row].height = 20
        is_alt = (s_no % 2 == 0)
        row_fill = ALT_ROW_FILL if is_alt else None

        # Build score lookup by question_id (preserve None for unread/unassigned marks)
        score_map = {
            s.get("question_id"): s.get("obtained_marks")
            for s in record.get("scores", [])
        }

        # S.No
        c1 = ws.cell(row=current_row, column=1, value=s_no)
        c1.alignment = ALIGN_CENTER
        c1.font = FONT_DATA
        c1.border = CELL_BORDER
        if row_fill: c1.fill = row_fill

        # Student ID
        c2 = ws.cell(row=current_row, column=2, value=str(record.get("student_id", "")))
        c2.alignment = ALIGN_CENTER
        c2.font = FONT_BOLD
        c2.border = CELL_BORDER
        if row_fill: c2.fill = row_fill

        # Student Name
        c3 = ws.cell(row=current_row, column=3, value=str(record.get("student_name", "Unknown")))
        c3.alignment = ALIGN_LEFT
        c3.font = FONT_DATA
        c3.border = CELL_BORDER
        if row_fill: c3.fill = row_fill

        # Question Scores
        col_offset = 4
        for q in questions:
            qid = q.get("question_id")
            val = score_map.get(qid)
            if val is not None:
                cq = ws.cell(row=current_row, column=col_offset, value=float(val))
                cq.alignment = ALIGN_RIGHT
                cq.number_format = "0.0"
            else:
                cq = ws.cell(row=current_row, column=col_offset, value="—")
                cq.alignment = ALIGN_CENTER
            cq.font = FONT_DATA
            cq.border = CELL_BORDER
            if row_fill: cq.fill = row_fill
            col_offset += 1

        # Total Obtained
        raw_tot = record.get("total_obtained")
        if raw_tot is not None:
            tot_obtained = float(raw_tot)
            scores_for_stats.append(tot_obtained)
            c_tot = ws.cell(row=current_row, column=col_offset, value=tot_obtained)
            c_tot.alignment = ALIGN_RIGHT
            c_tot.number_format = "0.0"
        else:
            c_tot = ws.cell(row=current_row, column=col_offset, value="—")
            c_tot.alignment = ALIGN_CENTER
        c_tot.font = FONT_BOLD
        c_tot.border = CELL_BORDER
        if row_fill: c_tot.fill = row_fill
        col_offset += 1

        # Max Marks
        tot_max = float(record.get("total_max", exam.get("total_marks", 0.0)))
        c_max = ws.cell(row=current_row, column=col_offset, value=tot_max)
        c_max.alignment = ALIGN_RIGHT
        c_max.font = FONT_DATA
        c_max.number_format = "0.0"
        c_max.border = CELL_BORDER
        if row_fill: c_max.fill = row_fill
        col_offset += 1

        # Percentage
        raw_pct = record.get("percentage")
        if raw_pct is not None:
            pct = float(raw_pct)
            c_pct = ws.cell(row=current_row, column=col_offset, value=pct / 100.0)
            c_pct.alignment = ALIGN_RIGHT
            c_pct.number_format = "0.0%"
        else:
            c_pct = ws.cell(row=current_row, column=col_offset, value="—")
            c_pct.alignment = ALIGN_CENTER
        c_pct.font = FONT_DATA
        c_pct.border = CELL_BORDER
        if row_fill: c_pct.fill = row_fill
        col_offset += 1

        # Status Badge
        status_val = str(record.get("status", "PENDING_REVIEW"))
        c_status = ws.cell(row=current_row, column=col_offset, value=status_val)
        c_status.alignment = ALIGN_CENTER
        c_status.border = CELL_BORDER
        if status_val == "APPROVED":
            c_status.font = FONT_APPROVED
            c_status.fill = APPROVED_FILL
        elif status_val == "NEEDS_CORRECTION":
            c_status.font = FONT_FLAG
            c_status.fill = FLAG_FILL
        else:
            c_status.font = FONT_PENDING
            c_status.fill = PENDING_FILL
        col_offset += 1

        # Approval Stamp
        app_by = record.get("approved_by") or "—"
        app_at = record.get("approved_at") or ""
        stamp_str = f"{app_by} ({app_at[:10]})" if app_at else app_by
        c_stamp = ws.cell(row=current_row, column=col_offset, value=stamp_str)
        c_stamp.alignment = ALIGN_CENTER
        c_stamp.font = FONT_DATA
        c_stamp.border = CELL_BORDER
        if row_fill: c_stamp.fill = row_fill

        current_row += 1

    # 6. Summary Footer Block (Statistics)
    if export_records:
        avg_score = round(sum(scores_for_stats) / len(scores_for_stats), 2)
        max_score = max(scores_for_stats)
        min_score = min(scores_for_stats)

        ws.row_dimensions[current_row].height = 24
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
        lbl_cell = ws.cell(row=current_row, column=1, value=f"EVALUATION SUMMARY ({len(export_records)} Students Evaluated)")
        lbl_cell.font = FONT_BOLD
        lbl_cell.fill = FOOTER_FILL
        lbl_cell.alignment = ALIGN_LEFT

        # Total Obtained summary column
        tot_col_idx = 4 + len(questions)
        c_avg = ws.cell(row=current_row, column=tot_col_idx, value=avg_score)
        c_avg.font = FONT_BOLD
        c_avg.fill = FOOTER_FILL
        c_avg.alignment = ALIGN_RIGHT
        c_avg.number_format = "0.0"

        # Apply borders to summary row
        for c in range(1, total_cols + 1):
            ws.cell(row=current_row, column=c).border = CELL_BORDER
            if not ws.cell(row=current_row, column=c).fill.start_color.rgb:
                ws.cell(row=current_row, column=c).fill = FOOTER_FILL

        # Extra stat line below
        current_row += 1
        ws.row_dimensions[current_row].height = 20
        stat_summary = f"Class Average: {avg_score} pts | Highest Score: {max_score} pts | Lowest Score: {min_score} pts"
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=total_cols)
        stat_cell = ws.cell(row=current_row, column=1, value=stat_summary)
        stat_cell.font = FONT_META_LABEL
        stat_cell.alignment = ALIGN_CENTER

    # 7. Auto-Fit Column Widths
    for col in ws.columns:
        if not col or col[0].column is None:
            continue
        col_letter = get_column_letter(int(col[0].column))
        max_len = 0
        for cell in col:
            # Skip merged title row in width calculation
            if cell.row is not None and (cell.row == 1 or cell.row > current_row - 2):
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Specific override for key columns
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 26

    # 8. Save to memory buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    clean_sub = exam.get("subject_code", "EXAM").replace(" ", "_")
    exam_type = exam.get("exam_type", "MID").replace("MID_SEMESTER", "MidSem").replace("END_SEMESTER", "EndSem")
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"SmartMarks_{clean_sub}_{exam_type}_{date_str}.xlsx"

    return buffer, filename
