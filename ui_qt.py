# -*- coding: utf-8 -*-
from pathlib import Path
import sys
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget
import app as logic
import guides as guide
import validator as text_validator
BASE=Path(__file__).resolve().parent
class Worker(QThread):
    done=Signal(list,str)
    def __init__(self,data): super().__init__(); self.data=data
    def run(self):
        try: texts=logic.ai_generate_variants(self.data,3) if logic.ai_is_enabled() else None; source='ИИ' if texts else 'шаблон'
        except Exception as e: print('ИИ недоступен:',e); texts=None; source='шаблон'
        if not texts:
            fn=logic.build_short_text if self.data['platform']=='Баннер' else logic.build_long_text; texts=[fn(self.data) for _ in range(3)]
        self.done.emit(texts,source)
class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('ИИ-помощник для генерации рекламы — Центр-инвест'); self.resize(1400,900); self.setMinimumSize(1050,700); self.data=None; self.worker=None; self.sources=['','','']; self._boxes=[]; self.build(); self.set_background()
    def build(self):
        root=QWidget(); root.setObjectName('root'); self.setCentralWidget(root); shell=QVBoxLayout(root); shell.setContentsMargins(30,24,30,24); shell.setSpacing(16)
        head=QFrame(objectName='glass'); hl=QVBoxLayout(head); hl.setContentsMargins(24,18,24,18); self.status=QLabel(self.status_text()); self.status.setObjectName('status'); title=QLabel('ИИ-помощник для генерации рекламы'); title.setObjectName('title'); sub=QLabel('Центр-инвест  •  адаптация под аудиторию  •  проверка текста'); sub.setObjectName('sub'); hl.addWidget(title); hl.addWidget(sub); hl.addWidget(self.status); shell.addWidget(head)
        body=QHBoxLayout(); body.setSpacing(16); shell.addLayout(body,1); left=QFrame(objectName='glass'); left.setMinimumWidth(390); left.setMaximumWidth(480); right=QFrame(objectName='glass'); body.addWidget(left); body.addWidget(right,1)
        ll=QVBoxLayout(left); ll.setContentsMargins(22,20,22,20); ll.setSpacing(8); ll.addWidget(self.heading('Параметры рекламы')); self.product=self.add_line(ll,'Название продукта'); self.description=self.add_text(ll,'Описание предложения',90); self.benefits=self.add_text(ll,'Преимущества (по одному в строке)',75); ll.addWidget(self.label('Цена / оффер')); self.price=QLineEdit(); ll.addWidget(self.price)
        grid=QGridLayout(); grid.setColumnStretch(0,1); grid.setColumnStretch(1,2); self.platform=QComboBox(); self.platform.addItems(guide.PLATFORMS); self.audience=QComboBox(); self.audience.addItems(guide.AUDIENCES); self.tone=QComboBox(); self.tone.addItems(guide.TONES_LIST); self.custom=QLineEdit(); grid.addWidget(self.label('Площадка'),0,0); grid.addWidget(self.label('Целевая аудитория'),0,1); grid.addWidget(self.platform,1,0); grid.addWidget(self.audience,1,1); grid.addWidget(self.label('Тональность'),2,0); grid.addWidget(self.label('Своя аудитория'),2,1); grid.addWidget(self.tone,3,0); grid.addWidget(self.custom,3,1); ll.addLayout(grid); ll.addStretch(1); self.gen=QPushButton('✨  Сгенерировать 3 варианта'); self.gen.setObjectName('primary'); self.gen.clicked.connect(self.generate); ll.addWidget(self.gen); clear=QPushButton('Очистить'); clear.clicked.connect(self.clear); ll.addWidget(clear)
        rl=QVBoxLayout(right); rl.setContentsMargins(22,20,22,20); rl.addWidget(self.heading('Сгенерированные тексты')); rl.addWidget(QLabel('Редактируйте текст во вкладке, затем проверьте или скопируйте вариант.')); self.tabs=QTabWidget(); rl.addWidget(self.tabs,1); self.editors=[]; self.lengths=[]
        for i in range(3):
            tab=QWidget(); tab.setObjectName('tabPage'); tl=QVBoxLayout(tab); length=QLabel('0 / 0 символов'); length.setAlignment(Qt.AlignRight); edit=QPlainTextEdit(); edit.setPlaceholderText('Здесь появится рекламный текст...'); edit.textChanged.connect(lambda i=i:self.update_length(i)); self.lengths.append(length); self.editors.append(edit); tl.addWidget(length); tl.addWidget(edit,1); row=QHBoxLayout()
            for text,fn in [('🔄 Перегенерировать',self.regenerate),('📋 Копировать',self.copy),('✅ Проверить',self.check)]: b=QPushButton(text); b.clicked.connect(lambda _,i=i,fn=fn:fn(i)); row.addWidget(b)
            row.addStretch(1); tl.addLayout(row); self.tabs.addTab(tab,f'✨ Вариант #{i+1}')
    def label(self,t): x=QLabel(t); x.setObjectName('label'); return x
    def heading(self,t): x=QLabel(t); x.setObjectName('heading'); return x
    def add_line(self,layout,label): box=QWidget(self); l=QVBoxLayout(box); l.setContentsMargins(0,0,0,0); l.addWidget(self.label(label)); e=QLineEdit(); l.addWidget(e); self._boxes.append(box); layout.addWidget(box); return e
    def add_text(self,layout,label,height): box=QWidget(self); l=QVBoxLayout(box); l.setContentsMargins(0,0,0,0); l.addWidget(self.label(label)); e=QPlainTextEdit(); e.setFixedHeight(height); l.addWidget(e); self._boxes.append(box); layout.addWidget(box); return e
    def status_text(self): return f'🤖 Модель: {logic.AI_MODEL}' if logic.ai_is_enabled() else '📋 ИИ выключен — доступна шаблонная генерация'
    def set_background(self):
        p=BASE/'fon.jpg'
        if p.exists(): self.setStyleSheet(STYLE+f"\nQMainWindow{{background-image:url('{p.as_posix()}');background-position:center;background-repeat:no-repeat;}}")
    def collect(self):
        if not self.product.text().strip(): QMessageBox.warning(self,'Внимание','Укажите название продукта.'); return None
        return {'product':self.product.text().strip(),'description':self.description.toPlainText().strip(),'benefits':[x.strip() for x in self.benefits.toPlainText().splitlines() if x.strip()],'price':self.price.text().strip(),'platform':self.platform.currentText(),'audience':self.audience.currentText(),'audience_custom':self.custom.text().strip(),'tone':self.tone.currentText()}
    def generate(self):
        d=self.collect()
        if not d or not d['description']: QMessageBox.warning(self,'Проверьте данные','Добавьте описание продукта.'); return
        self.data=d; self.gen.setEnabled(False); self.status.setText('⏳ Создание текстов...'); self.worker=Worker(d); self.worker.done.connect(self.finished); self.worker.start()
    def finished(self,texts,source):
        self.gen.setEnabled(True); self.status.setText(f'Последняя генерация: {source}')
        for i,t in enumerate(texts): self.sources[i]=source; self.editors[i].setPlainText(t); self.update_length(i)
    def update_length(self,i):
        if self.data:self.lengths[i].setText(f"{len(self.editors[i].toPlainText())} / {guide.PLATFORM_LIMITS[self.data['platform']][1]} символов · {self.sources[i]}")
    def regenerate(self,i):
        if not self.data:return
        limit=guide.PLATFORM_LIMITS[self.data['platform']][1]
        t,r,n=text_validator.validate_and_rewrite(self.editors[i].toPlainText(),limit,logic.rewrite_with_ai)
        self.sources[i]='ИИ'; self.editors[i].setPlainText(t); self.update_length(i)
        m=r['errors']
        (QMessageBox.warning if m else QMessageBox.information)(
            self,'Перегенерация',
            ('После '+str(n)+' попыток остались ошибки:\n\n'+'\n'.join(m))
            if m else ('Исправлено за '+str(n)+' попыток.'))
    def copy(self,i): QApplication.clipboard().setText(self.editors[i].toPlainText())
    def check(self,i):
        if not self.data:return
        r=text_validator.validate_text(self.editors[i].toPlainText(),max_length=guide.PLATFORM_LIMITS[self.data['platform']][1]); m=r['errors']+r['warnings']; (QMessageBox.warning if m else QMessageBox.information)(self,'Проверка','\n'.join(m) if m else 'Текст соответствует базовым требованиям.')
    def clear(self):
        for w in [self.product,self.price,self.custom]:w.clear()
        self.description.clear(); self.benefits.clear(); self.data=None
        for e,l in zip(self.editors,self.lengths):e.clear();l.setText('0 / 0 символов')
STYLE="""QMainWindow{background:#F0F7FF;} QWidget#root{background:rgba(240,247,255,80);color:#0F2942;font-family:'Segoe UI';font-size:10pt;} QFrame#glass{background:rgba(255,255,255,155);border-radius:20px;} QLabel#title{color:#0F2942;font-size:22pt;font-weight:700;} QLabel#sub,QLabel#status{color:#3B5978;} QLabel#heading{color:#0F2942;font-size:14pt;font-weight:700;} QLabel#label{color:#0F2942;font-weight:600;} QLineEdit,QPlainTextEdit,QComboBox{background:rgba(236,247,247,215);color:#0F2942;border:2px solid rgba(133,207,207,180);border-radius:16px;padding:8px;} QLineEdit:focus,QPlainTextEdit:focus,QComboBox:focus{border-color:#3BA6A6;} QPushButton{background:rgba(236,247,247,190);color:#0369A1;border:2px solid rgba(133,207,207,180);border-radius:12px;padding:9px 14px;font-weight:600;} QPushButton:hover{background:#D6E6E6;border-color:#3BA6A6;} QPushButton#primary{background:rgba(186,230,253,225);color:#0C4A6E;border-color:#7DD3FC;font-size:11pt;} QTabWidget,QTabWidget::pane,QTabBar{background:transparent;border:0;} QTabBar::tab{background:rgba(224,242,254,205);color:#3B5978;padding:9px 16px;border-radius:10px;margin-right:4px;font-weight:600;} QTabBar::tab:selected{background:rgba(186,230,253,230);color:#0369A1;} QWidget#tabPage{background:transparent;}"""
def main(): app=QApplication(sys.argv); app.setStyleSheet(STYLE); w=Window(); w.show(); sys.exit(app.exec())
if __name__=='__main__': main()
