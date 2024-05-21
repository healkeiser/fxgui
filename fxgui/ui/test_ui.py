# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'test.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialogButtonBox, QDockWidget, QDoubleSpinBox, QFontComboBox,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListView,
    QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar,
    QPushButton, QRadioButton, QScrollBar, QSizePolicy,
    QSlider, QSpacerItem, QSpinBox, QTabWidget,
    QTableView, QTextBrowser, QToolBox, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1307, 935)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(Form)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabBarAutoHide(False)
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout = QGridLayout(self.tab)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame = QFrame(self.tab)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Plain)
        self.frame.setLineWidth(0)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.button_success = QPushButton(self.frame)
        self.button_success.setObjectName(u"button_success")

        self.horizontalLayout.addWidget(self.button_success)

        self.button_info = QPushButton(self.frame)
        self.button_info.setObjectName(u"button_info")

        self.horizontalLayout.addWidget(self.button_info)

        self.button_warning = QPushButton(self.frame)
        self.button_warning.setObjectName(u"button_warning")

        self.horizontalLayout.addWidget(self.button_warning)

        self.button_error = QPushButton(self.frame)
        self.button_error.setObjectName(u"button_error")

        self.horizontalLayout.addWidget(self.button_error)

        self.button_critical = QPushButton(self.frame)
        self.button_critical.setObjectName(u"button_critical")

        self.horizontalLayout.addWidget(self.button_critical)


        self.gridLayout.addWidget(self.frame, 8, 1, 1, 2)

        self.label = QLabel(self.tab)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 3, 1, 1, 1)

        self.lineEdit_3 = QLineEdit(self.tab)
        self.lineEdit_3.setObjectName(u"lineEdit_3")
        self.lineEdit_3.setEnabled(False)

        self.gridLayout.addWidget(self.lineEdit_3, 4, 2, 1, 1)

        self.label_2 = QLabel(self.tab)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setEnabled(False)

        self.gridLayout.addWidget(self.label_2, 4, 1, 1, 1)

        self.doubleSpinBox = QDoubleSpinBox(self.tab)
        self.doubleSpinBox.setObjectName(u"doubleSpinBox")

        self.gridLayout.addWidget(self.doubleSpinBox, 0, 1, 1, 1)

        self.comboBox = QComboBox(self.tab)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")

        self.gridLayout.addWidget(self.comboBox, 0, 2, 1, 1)

        self.fontComboBox = QFontComboBox(self.tab)
        self.fontComboBox.setObjectName(u"fontComboBox")

        self.gridLayout.addWidget(self.fontComboBox, 1, 2, 1, 1)

        self.lineEdit_2 = QLineEdit(self.tab)
        self.lineEdit_2.setObjectName(u"lineEdit_2")

        self.gridLayout.addWidget(self.lineEdit_2, 3, 2, 1, 1)

        self.spinBox = QSpinBox(self.tab)
        self.spinBox.setObjectName(u"spinBox")

        self.gridLayout.addWidget(self.spinBox, 1, 1, 1, 1)

        self.horizontalScrollBar = QScrollBar(self.tab)
        self.horizontalScrollBar.setObjectName(u"horizontalScrollBar")
        self.horizontalScrollBar.setOrientation(Qt.Horizontal)

        self.gridLayout.addWidget(self.horizontalScrollBar, 5, 1, 1, 2)

        self.plainTextEdit = QPlainTextEdit(self.tab)
        self.plainTextEdit.setObjectName(u"plainTextEdit")

        self.gridLayout.addWidget(self.plainTextEdit, 2, 1, 1, 2)

        self.horizontalSlider = QSlider(self.tab)
        self.horizontalSlider.setObjectName(u"horizontalSlider")
        self.horizontalSlider.setOrientation(Qt.Horizontal)

        self.gridLayout.addWidget(self.horizontalSlider, 6, 1, 1, 2)

        self.progressBar_2 = QProgressBar(self.tab)
        self.progressBar_2.setObjectName(u"progressBar_2")
        self.progressBar_2.setValue(24)

        self.gridLayout.addWidget(self.progressBar_2, 7, 1, 1, 2)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_2 = QGridLayout(self.tab_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.treeWidget = QTreeWidget(self.tab_2)
        __qtreewidgetitem = QTreeWidgetItem(self.treeWidget)
        QTreeWidgetItem(__qtreewidgetitem)
        QTreeWidgetItem(self.treeWidget)
        __qtreewidgetitem1 = QTreeWidgetItem(self.treeWidget)
        __qtreewidgetitem2 = QTreeWidgetItem(__qtreewidgetitem1)
        QTreeWidgetItem(__qtreewidgetitem2)
        QTreeWidgetItem(__qtreewidgetitem1)
        self.treeWidget.setObjectName(u"treeWidget")
        self.treeWidget.setSortingEnabled(True)
        self.treeWidget.setAnimated(True)

        self.gridLayout_2.addWidget(self.treeWidget, 0, 0, 1, 1)

        self.listWidget = QListWidget(self.tab_2)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        QListWidgetItem(self.listWidget)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setAlternatingRowColors(True)

        self.gridLayout_2.addWidget(self.listWidget, 0, 1, 1, 1)

        self.tableView = QTableView(self.tab_2)
        self.tableView.setObjectName(u"tableView")

        self.gridLayout_2.addWidget(self.tableView, 1, 0, 1, 2)

        self.buttonBox = QDialogButtonBox(self.tab_2)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)

        self.gridLayout_2.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.gridLayout_3 = QGridLayout(self.tab_3)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.radioButton_2 = QRadioButton(self.tab_3)
        self.radioButton_2.setObjectName(u"radioButton_2")
        self.radioButton_2.setEnabled(False)

        self.gridLayout_3.addWidget(self.radioButton_2, 4, 0, 1, 1)

        self.checkBox_3 = QCheckBox(self.tab_3)
        self.checkBox_3.setObjectName(u"checkBox_3")
        self.checkBox_3.setChecked(True)

        self.gridLayout_3.addWidget(self.checkBox_3, 5, 1, 1, 1)

        self.checkBox_2 = QCheckBox(self.tab_3)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setEnabled(False)

        self.gridLayout_3.addWidget(self.checkBox_2, 4, 1, 1, 1)

        self.progressBar = QProgressBar(self.tab_3)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(24)

        self.gridLayout_3.addWidget(self.progressBar, 2, 0, 1, 2)

        self.textBrowser = QTextBrowser(self.tab_3)
        self.textBrowser.setObjectName(u"textBrowser")

        self.gridLayout_3.addWidget(self.textBrowser, 1, 0, 1, 2)

        self.radioButton_3 = QRadioButton(self.tab_3)
        self.radioButton_3.setObjectName(u"radioButton_3")

        self.gridLayout_3.addWidget(self.radioButton_3, 5, 0, 1, 1)

        self.checkBox = QCheckBox(self.tab_3)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_3.addWidget(self.checkBox, 3, 1, 1, 1)

        self.radioButton = QRadioButton(self.tab_3)
        self.radioButton.setObjectName(u"radioButton")

        self.gridLayout_3.addWidget(self.radioButton, 3, 0, 1, 1)

        self.toolBox = QToolBox(self.tab_3)
        self.toolBox.setObjectName(u"toolBox")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.page.setGeometry(QRect(0, 0, 1265, 330))
        self.horizontalLayout_2 = QHBoxLayout(self.page)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.groupBox = QGroupBox(self.page)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.lineEdit = QLineEdit(self.groupBox)
        self.lineEdit.setObjectName(u"lineEdit")

        self.verticalLayout_2.addWidget(self.lineEdit)

        self.listView_2 = QListView(self.groupBox)
        self.listView_2.setObjectName(u"listView_2")

        self.verticalLayout_2.addWidget(self.listView_2)


        self.horizontalLayout_2.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(self.page)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.listView = QListView(self.groupBox_2)
        self.listView.setObjectName(u"listView")

        self.verticalLayout_3.addWidget(self.listView)

        self.buttonBox_2 = QDialogButtonBox(self.groupBox_2)
        self.buttonBox_2.setObjectName(u"buttonBox_2")
        self.buttonBox_2.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout_3.addWidget(self.buttonBox_2)


        self.horizontalLayout_2.addWidget(self.groupBox_2)

        self.toolBox.addItem(self.page, u"Page 1")
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.page_2.setGeometry(QRect(0, 0, 100, 30))
        self.toolBox.addItem(self.page_2, u"Page 2")

        self.gridLayout_3.addWidget(self.toolBox, 0, 0, 1, 2)

        self.tabWidget.addTab(self.tab_3, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.gridLayout_4 = QGridLayout(self.tab_4)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.dockWidget = QDockWidget(self.tab_4)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.dockWidget.setWidget(self.dockWidgetContents)

        self.gridLayout_4.addWidget(self.dockWidget, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_4, "")

        self.verticalLayout.addWidget(self.tabWidget)


        self.retranslateUi(Form)

        self.tabWidget.setCurrentIndex(0)
        self.toolBox.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.button_success.setText(QCoreApplication.translate("Form", u"Success", None))
        self.button_info.setText(QCoreApplication.translate("Form", u"Info", None))
        self.button_warning.setText(QCoreApplication.translate("Form", u"Warning", None))
        self.button_error.setText(QCoreApplication.translate("Form", u"Error", None))
        self.button_critical.setText(QCoreApplication.translate("Form", u"Critical", None))
        self.label.setText(QCoreApplication.translate("Form", u"Enabled", None))
        self.lineEdit_3.setPlaceholderText(QCoreApplication.translate("Form", u"Disabled...", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Disabled", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("Form", u"New Item", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("Form", u"New Item", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("Form", u"New Item", None))
        self.comboBox.setItemText(3, QCoreApplication.translate("Form", u"New Item", None))
        self.comboBox.setItemText(4, QCoreApplication.translate("Form", u"New Item", None))
        self.comboBox.setItemText(5, QCoreApplication.translate("Form", u"New Item", None))
        self.comboBox.setItemText(6, QCoreApplication.translate("Form", u"New Item", None))

        self.lineEdit_2.setPlaceholderText(QCoreApplication.translate("Form", u"Enabled...", None))
        self.plainTextEdit.setPlainText(QCoreApplication.translate("Form", u"Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("Form", u"Tab 1", None))
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("Form", u"New Column", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("Form", u"New Column", None));

        __sortingEnabled = self.treeWidget.isSortingEnabled()
        self.treeWidget.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.treeWidget.topLevelItem(0)
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("Form", u"New Item", None));
        ___qtreewidgetitem2 = ___qtreewidgetitem1.child(0)
        ___qtreewidgetitem2.setText(0, QCoreApplication.translate("Form", u"New Subitem", None));
        ___qtreewidgetitem3 = self.treeWidget.topLevelItem(1)
        ___qtreewidgetitem3.setText(0, QCoreApplication.translate("Form", u"New Item", None));
        ___qtreewidgetitem4 = self.treeWidget.topLevelItem(2)
        ___qtreewidgetitem4.setText(0, QCoreApplication.translate("Form", u"New Item", None));
        ___qtreewidgetitem5 = ___qtreewidgetitem4.child(0)
        ___qtreewidgetitem5.setText(0, QCoreApplication.translate("Form", u"New Subitem", None));
        ___qtreewidgetitem6 = ___qtreewidgetitem5.child(0)
        ___qtreewidgetitem6.setText(0, QCoreApplication.translate("Form", u"New Subitem", None));
        ___qtreewidgetitem7 = ___qtreewidgetitem4.child(1)
        ___qtreewidgetitem7.setText(0, QCoreApplication.translate("Form", u"New Subitem", None));
        self.treeWidget.setSortingEnabled(__sortingEnabled)


        __sortingEnabled1 = self.listWidget.isSortingEnabled()
        self.listWidget.setSortingEnabled(False)
        ___qlistwidgetitem = self.listWidget.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem1 = self.listWidget.item(1)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem2 = self.listWidget.item(2)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem3 = self.listWidget.item(3)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem4 = self.listWidget.item(4)
        ___qlistwidgetitem4.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem5 = self.listWidget.item(5)
        ___qlistwidgetitem5.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem6 = self.listWidget.item(6)
        ___qlistwidgetitem6.setText(QCoreApplication.translate("Form", u"New Item", None));
        ___qlistwidgetitem7 = self.listWidget.item(7)
        ___qlistwidgetitem7.setText(QCoreApplication.translate("Form", u"New Item", None));
        self.listWidget.setSortingEnabled(__sortingEnabled1)

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("Form", u"Tab 2", None))
        self.radioButton_2.setText(QCoreApplication.translate("Form", u"RadioButton", None))
        self.checkBox_3.setText(QCoreApplication.translate("Form", u"CheckBox", None))
        self.checkBox_2.setText(QCoreApplication.translate("Form", u"CheckBox", None))
        self.textBrowser.setHtml(QCoreApplication.translate("Form", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'MS Shell Dlg 2'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:8pt;\">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</span></p></body></html>", None))
        self.radioButton_3.setText(QCoreApplication.translate("Form", u"RadioButton", None))
        self.checkBox.setText(QCoreApplication.translate("Form", u"CheckBox", None))
        self.radioButton.setText(QCoreApplication.translate("Form", u"RadioButton", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"GroupBox", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Form", u"GroupBox", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page), QCoreApplication.translate("Form", u"Page 1", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.page_2), QCoreApplication.translate("Form", u"Page 2", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("Form", u"Tab 3", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("Form", u"Page", None))
    # retranslateUi

