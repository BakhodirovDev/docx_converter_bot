from docx import Document


def convert_docx_to_txt(docx_path: str, txt_path: str) -> str:
    """
    DOCX fayldan savol-javoblarni extract qilib TXT ga yozadi.
    
    Format:
    ? Savol matni
    + To'g'ri javob
    - Noto'g'ri javob 1
    - Noto'g'ri javob 2
    """
    doc = Document(docx_path)
    
    with open(txt_path, 'w', encoding='utf-8') as file:
        # Jadvallardagi savol-javoblarni extract qilish
        for table in doc.tables:
            for row in table.rows:
                # Birinchi ustun - savol
                question = row.cells[0].text.strip()
                
                # Qolgan ustunlar - javoblar
                answers = [cell.text.strip() for cell in row.cells[1:]]
                
                if question:  # Faqat savol bo'lsa yozamiz
                    file.write(f"? {question}\n")
                    
                    # Birinchi javob - to'g'ri javob (+)
                    if len(answers) > 0 and answers[0]:
                        file.write(f"+ {answers[0]}\n")
                    
                    # Qolgan javoblar - noto'g'ri javoblar (-)
                    for ans in answers[1:]:
                        if ans:  # Bo'sh bo'lmasa
                            file.write(f"- {ans}\n")
                    
                    file.write("\n")  # Har bir savol-javobdan keyin bo'sh qator
    
    return txt_path
