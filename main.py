import pdfplumber
import os
import json
import re
from collections import defaultdict, Counter
import datetime # For timestamp

# Docker-aware input/output - THESE MUST COME FIRST
IN_DOCKER = os.path.exists("/app/input") and os.path.exists("/app/output")
INPUT_DIR = "/app/input" if IN_DOCKER else "./input"
OUTPUT_DIR = "/app/output" if IN_DOCKER else "./output"

# Now, define files that depend on INPUT_DIR/OUTPUT_DIR
PERSONA_FILE = os.path.join(INPUT_DIR, "persona.txt") # Or persona.json
JOB_TO_BE_DONE_FILE = os.path.join(INPUT_DIR, "job_to_be_done.txt")


# --- Your existing functions follow below ---

def group_lines(words, y_tolerance=3):
    lines = defaultdict(list)
    for word in words:
        added = False
        for y in lines:
            if abs(word['top'] - y) <= y_tolerance:
                lines[y].append(word)
                added = True
                break
        if not added:
            lines[word['top']].append(word)
    sorted_lines = sorted(lines.values(), key=lambda line: line[0]['top'])
    return [sorted(line, key=lambda w: w['x0']) for line in sorted_lines]

def is_bold(word):
    font = word.get("fontname", "").lower()
    return "bold" in font or "black" in font or "demi" in font

def get_color_tuple(word):
    color = word.get("non_stroking_color")
    if isinstance(color, (list, tuple)) and all(isinstance(x, (int, float)) for x in color):
        return tuple(color)
    return None

def extract_outline(pdf_path):
    outline = []
    title = ""
    all_font_sizes = []
    all_colors = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:5]:
            words = page.extract_words(extra_attrs=["size", "non_stroking_color", "fontname"])
            all_font_sizes.extend([w['size'] for w in words if 'size' in w])
            all_colors.extend([get_color_tuple(w) for w in words if get_color_tuple(w)])

        if not all_font_sizes:
            return {"title": "", "outline": []}

        body_font_size = Counter(all_font_sizes).most_common(1)[0][0]
        potential_heading_sizes = sorted(list(set(s for s in all_font_sizes if s > body_font_size)), reverse=True)
        heading_sizes = potential_heading_sizes[:3]
        size_to_level = {size: f"H{i+1}" for i, size in enumerate(heading_sizes)}
        common_colors = [color for color, _ in Counter(all_colors).most_common(5)]

        for page_idx in range(min(2, len(pdf.pages))):
            page = pdf.pages[page_idx]
            words = page.extract_words(extra_attrs=["size"])
            lines = group_lines(words)
            
            for line in lines:
                if not line:
                    continue
                first_word = line[0]
                font_size = first_word.get("size")
                full_text = " ".join(w['text'] for w in line).strip()
                
                if potential_heading_sizes and font_size == potential_heading_sizes[0] and len(full_text) < 100:
                    title = full_text
                    break
            if title:
                break

        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(extra_attrs=["size", "fontname", "non_stroking_color"])
            lines = group_lines(words)

            line_gaps = []
            for i in range(1, len(lines)):
                top = lines[i][0]['top']
                prev_bottom = lines[i - 1][-1]['bottom']
                gap = top - prev_bottom
                if gap > 0:
                    line_gaps.append(gap)
            avg_body_gap = sum(line_gaps) / len(line_gaps) if line_gaps else 5

            for i, line in enumerate(lines):
                if not line:
                    continue

                first_word = line[0]
                font_size = first_word.get("size", body_font_size)
                font_color = get_color_tuple(first_word)
                indent = first_word.get("x0", 999)
                bold = is_bold(first_word)
                top = first_word.get("top", 0)

                full_text = " ".join(w['text'] for w in line).strip()
                
                if len(full_text) > 100 or len(full_text) < 3:
                    continue

                gap_above = 0
                if i > 0:
                    prev_bottom = lines[i - 1][-1]['bottom']
                    gap_above = top - prev_bottom
                    
                score = 0
                
                if font_size in heading_sizes:
                    score += 3 if font_size == heading_sizes[0] else (2 if font_size == heading_sizes[1] else 1)
                
                if bold:
                    score += 2
                
                if font_color and font_color not in common_colors:
                    score += 1

                if indent < 70:
                    score += 1
                
                if gap_above > (avg_body_gap * 1.5):
                    score += 1
                    
                if full_text.isupper() and len(full_text) < 50:
                    score += 1.5
                elif full_text.istitle() and not (full_text.lower().startswith("the ") or full_text.lower().startswith("a ")):
                    score += 1

                if re.match(r"^\d+(\.\d+)*\s+[A-Za-z]", full_text):
                    score += 2

                if len(line) <= 5 and score >= 3:
                    score += 1

                if score >= 4:
                    level = "H3"
                    if font_size in size_to_level:
                        level = size_to_level[font_size]
                    else:
                        if font_size > body_font_size and bold:
                            if font_size >= heading_sizes[0]: level = "H1"
                            elif len(heading_sizes) > 1 and font_size >= heading_sizes[1]: level = "H2"
                            else: level = "H3"

                    if not outline or (full_text.lower() != outline[-1]['text'].lower() and not full_text.lower().startswith(outline[-1]['text'].lower())):
                        outline.append({
                            "level": level,
                            "text": full_text,
                            "page": page_num + 1
                        })

    return {
        "title": title.strip(),
        "outline": outline
    }

def extract_text_for_sections(pdf_path, outline):
    """
    Extracts content for each section defined by the outline.
    This is a crucial step for Round 1B.
    """
    sections_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, heading in enumerate(outline):
            start_page_num = heading['page'] - 1 # Convert to 0-indexed
            heading_text = heading['text']

            # Determine end of section: either next heading's page/position or end of document
            end_page_num = len(pdf.pages) - 1
            next_heading_top = None

            if i + 1 < len(outline):
                next_heading = outline[i+1]
                next_heading_page_num = next_heading['page'] - 1
                
                # Try to find the actual vertical position of the next heading on its page
                # This makes extraction more precise than just page boundaries.
                next_heading_words = pdf.pages[next_heading_page_num].extract_words()
                for word in next_heading_words:
                    if next_heading['text'].lower() in word['text'].lower(): # Simple match
                        next_heading_top = word['top']
                        break
                # If next heading is on a later page, or not found on current page after current heading,
                # then current section goes till end of current page.
                if next_heading_top is None and next_heading_page_num > start_page_num:
                     end_page_num = next_heading_page_num - 1 # Current section ends before next heading's page

            current_section_text = []
            for p_idx in range(start_page_num, end_page_num + 1):
                page = pdf.pages[p_idx]
                page_text = page.extract_text()
                
                # If on the start page, exclude content *before* the current heading
                if p_idx == start_page_num:
                    lines = page_text.split('\n')
                    start_reading = False
                    for line in lines:
                        if heading_text.lower() in line.lower():
                            start_reading = True
                            current_section_text.append(line) # Include the heading itself
                        elif start_reading:
                            current_section_text.append(line)
                # If on the end page, and next heading on same page, exclude content *after* the next heading
                elif p_idx == end_page_num and next_heading_top is not None:
                    # More advanced: extract words with coordinates and filter by y-position
                    words_on_page = page.extract_words()
                    filtered_words = [word['text'] for word in words_on_page if word['top'] < next_heading_top]
                    current_section_text.append(" ".join(filtered_words)) # Join filtered words for the line
                else: # Full page content
                    current_section_text.append(page_text)
            
            # Join text and clean up
            section_full_text = "\n".join(current_section_text).strip()
            
            sections_content.append({
                "document": os.path.basename(pdf_path),
                "page_number": heading['page'],
                "section_title": heading_text,
                "full_text": section_full_text
            })
    return sections_content

def analyze_documents_for_persona(pdf_files, persona_description, job_to_be_done):
    """
    Main logic for Round 1B: analyzes documents based on persona and job-to-be-done.
    """
    all_extracted_sections = []
    
    # 1. Process each PDF to get its outline and then its full section texts
    for pdf_file_path in pdf_files:
        print(f"  Extracting outline for {os.path.basename(pdf_file_path)}")
        outline_data = extract_outline(pdf_file_path) 
        
        sections_with_content = extract_text_for_sections(pdf_file_path, outline_data['outline'])
        all_extracted_sections.extend(sections_with_content)

    # 2. Analyze persona and job-to-be-done
    print("  Analyzing persona and job-to-be-done...")
    persona_keywords = set(word.lower() for word in re.findall(r'\b\w+\b', persona_description) if len(word) > 2)
    job_keywords = set(word.lower() for word in re.findall(r'\b\w+\b', job_to_be_done) if len(word) > 2)
    
    relevant_keywords = persona_keywords.union(job_keywords)
    stopwords = {"the", "a", "an", "is", "of", "to", "and", "or", "for", "in", "on", "with", "as", "by", "from", "at", "be"}
    relevant_keywords = {kw for kw in relevant_keywords if kw not in stopwords}


    # 3. Score and Rank Sections
    print("  Scoring and ranking sections...")
    scored_sections = []
    for section in all_extracted_sections:
        section_text_lower = section['full_text'].lower()
        
        score = sum(1 for keyword in relevant_keywords if keyword in section_text_lower)
        
        if len(section_text_lower) < 50 and score > 0:
            score *= 0.5
        elif len(section_text_lower) > 500:
            score *= 1.1

        scored_sections.append({
            **section,
            "relevance_score": score
        })
    
    scored_sections.sort(key=lambda x: x['relevance_score'], reverse=True)

    # 4. Refine Sub-sections
    final_extracted_sections = []
    final_sub_section_analysis = []
    
    top_n_sections = 10
    
    for rank, section in enumerate(scored_sections[:top_n_sections]):
        if section['relevance_score'] == 0:
            continue

        final_extracted_sections.append({
            "document": section['document'],
            "page_number": section['page_number'],
            "section_title": section['section_title'],
            "importance_rank": rank + 1
        })

        refined_text = section['full_text'].split('\n')[0] + "..." if len(section['full_text']) > 200 else section['full_text']
        
        final_sub_section_analysis.append({
            "document": section['document'],
            "page_number": section['page_number'],
            "refined_text": refined_text
        })
            
    return final_extracted_sections, final_sub_section_analysis


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"DEBUG: Contents of INPUT_DIR ({INPUT_DIR}):")
    try:
        for f in os.listdir(INPUT_DIR):
            print(f"  - {f}")
    except FileNotFoundError:
        print("  INPUT_DIR not found!")
    print("--- End DEBUG ---")

    pdf_files_in_input = [
        os.path.join(INPUT_DIR, f) 
        for f in os.listdir(INPUT_DIR) 
        if f.lower().endswith(".pdf")
    ]
    
    if not pdf_files_in_input:
        print(f"No PDF files found in {INPUT_DIR}. Exiting.")
        return

    # --- Round 1B Specific Input Reading ---
    persona_description = ""
    job_to_be_done = ""

    if os.path.exists(PERSONA_FILE):
        with open(PERSONA_FILE, 'r', encoding='utf-8') as f:
            persona_description = f.read().strip()
        print(f"Read persona from {PERSONA_FILE}")
    else:
        print(f"Warning: {PERSONA_FILE} not found. Persona will be empty.")

    if os.path.exists(JOB_TO_BE_DONE_FILE):
        with open(JOB_TO_BE_DONE_FILE, 'r', encoding='utf-8') as f:
            job_to_be_done = f.read().strip()
        print(f"Read job-to-be-done from {JOB_TO_BE_DONE_FILE}")
    else:
        print(f"Warning: {JOB_TO_BE_DONE_FILE} not found. Job-to-be-done will be empty.")


    if not persona_description or not job_to_be_done:
        print("Error: Persona or Job-to-be-done not provided. Cannot proceed with Round 1B analysis.")
        return


    # --- Execute Round 1B Logic ---
    print(f"\nStarting Round 1B analysis for {len(pdf_files_in_input)} documents...")
    print(f"Persona: {persona_description[:50]}...")
    print(f"Job: {job_to_be_done[:50]}...")

    extracted_sections_output, sub_section_analysis_output = \
        analyze_documents_for_persona(pdf_files_in_input, persona_description, job_to_be_done)

    final_output_data = {
        "metadata": {
            "input_documents": [os.path.basename(f) for f in pdf_files_in_input],
            "persona": persona_description,
            "job_to_be_done": job_to_be_done,
            "processing_timestamp": datetime.datetime.now().isoformat()
        },
        "extracted_sections": extracted_sections_output,
        "sub_section_analysis": sub_section_analysis_output
    }

    output_file_name = "challenge1b_results.json"
    output_path = os.path.join(OUTPUT_DIR, output_file_name)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Round 1B analysis complete. Results saved to: {output_path}")
    print(f"Output Preview:\n{json.dumps(final_output_data, indent=2, ensure_ascii=False)[:1000]}...")


if __name__ == "__main__":
    main()