from xhtml2pdf import pisa
import io

def test_pdf():
    html = "<html><body><h1>Test</h1></body></html>"
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        print("PDF generated successfully")
    else:
        print("Error during PDF generation:", pdf.err)

if __name__ == "__main__":
    test_pdf()
