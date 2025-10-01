
def app_stylesheet() -> str:
    return """
QPushButton {
    background-color: #1c0c29;
    color: cyan;
    padding: 10px 20px;
    border: 1px solid #4CA;
    border-radius: 8px;
    font-size: 16px;
    min-width: 260px;
}
QPushButton:hover {
    background-color: #502275;
    color: #ffe08a;
    border: 1px solid #134639;
}
QPushButton:pressed {
    background-color: #7130a5;
    color: #ffe08a;
    border: 1px solid #0c2922;
}
QPushButton:disabled {
    background-color: #2a1f38;
    color: #8e8e8e;
    border: 1px solid #3a3a3a;
}
QLabel.header {
    color: #f0f0ff;
    font-size: 28px;
    font-weight: bold;
    padding: 8px 0 18px 0;
    letter-spacing: 1px;
}
/* Solid panels for readability */
QGroupBox {
    color: #e8e8ff;
    font-weight: bold;
    margin-top: 12px;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 8px;
    background-color: rgba(12, 30, 64, 0.80);
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
/* Tables with bold headers, cyan selected text */
QTableView {
    gridline-color: #666;
    selection-background-color: #2f6d9b;
    selection-color: cyan;
    alternate-background-color: rgba(255,255,255,0.06);
    background: rgba(5, 20, 45, 0.70);
    color: #f3f3f3;
}
QHeaderView::section {
    background: #1b3a6b;
    color: #f0f0f0;
    font-weight: 700;
    padding: 6px;
    border: none;
    border-right: 1px solid rgba(255,255,255,0.08);
}
"""
