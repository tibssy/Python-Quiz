from kivy.app import App
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen
from kivy.animation import Animation
from kivy.uix.label import Label
from kivy.utils import get_color_from_hex
from kivy.properties import NumericProperty
from kivy.metrics import sp

# Built-in
from random import sample, shuffle
import math
import json

# Java Related
from android.runnable import run_on_ui_thread
from jnius import autoclass


Color = autoclass("android.graphics.Color")
WindowManager = autoclass('android.view.WindowManager$LayoutParams')
activity = autoclass('org.kivy.android.PythonActivity').mActivity

class ContainerScreen(BoxLayout):
    pass

class MainScreen(Screen):
    pass

class PythonQuizApp(App):
    data = json.load(open("quiz.json"))
    primary_color = get_color_from_hex('#F2DCA5')
    secondary_color = get_color_from_hex('#243441')
    tertiary_color = [math.sqrt(i) for i in primary_color]
    quaternary_color = [math.sqrt(j) for j in secondary_color]
    timer = NumericProperty(2400)
    number_of_question = 36
    your_answer = []
    score = 0

    def build(self):
        return ContainerScreen()

    def reset_app(self):
        self.set_number_of_questions()
        self.timer = self.duration
        self.score = 0
        self.root.ids.scrll_grd.clear_widgets()

    def set_button(self, func, val):
        number = self.number_of_question
        time = self.timer
        if func:
            number += val
        else:
            time += val
        self.number_of_question = number if number in range(1, len(self.data) + 1) else self.number_of_question
        self.timer = time if time in range(60, 5401) else self.timer
        self.set_number_of_questions()
        self.update_timer()

    def set_number_of_questions(self):
        self.root.ids.num_lbl.text = f'Questions:\n[b]{self.number_of_question}[/b]'

    def update_timer(self):
        self.root.ids.tm_lbl.text = f'Timer:\n[b]{int(self.timer // 60):02d}:{int(self.timer % 60):02d}[/b]'

    def update_number(self):
        self.root.ids.num_lbl.text = f'Questions:\n[b]{self.number_of_question - len(self.quiz_questions)}/{self.number_of_question}[/b]'

    def start_quiz(self):
        self.duration = self.timer
        self.quiz_questions = sample(range(len(self.data)), self.number_of_question)
        self.question_picker()
        self.start_timer()

    def start_timer(self):
        Animation.cancel_all(self)
        self.anim = Animation(timer=0, duration=self.timer)
        self.anim.bind(on_complete=self.timeout)
        self.anim.start(self)

    def on_timer(self, *args):
        self.update_timer()

    def timeout(self, *args):
        self.quiz_questions.append(self.question_index)
        for missed in self.quiz_questions:
            self.type = self.data[missed]['type']
            self.question = self.data[missed]['question']
            self.code = self.data[missed]['code']
            self.your_answer = []
            self.correct_answer = self.data[missed]['answer']
            self.add_to_scroll()
        self.score_report()

    def question_picker(self):
        remaining_question = len(self.quiz_questions)
        if remaining_question:
            self.root.ids.next_qstn.text = 'Finish' if remaining_question == 1 else 'Next'
            self.question_index = self.quiz_questions.pop()
            self.selected_question = self.data[self.question_index]

            self.type = self.selected_question['type']
            self.question = self.selected_question['question']
            self.code = self.selected_question['code']
            self.options = self.selected_question['options']
            self.correct_answer = self.selected_question['answer']

            shuffle(self.options)

            self.update_number()
            self.create_layout()
        else:
            self.score_report()

    def create_layout(self):
        self.root.ids.opt_cntnr.clear_widgets()
        if self.type == 'dropdownSelect':
            self.dropdown_select()
        else:
            self.single_multiple_choice()

    def single_multiple_choice(self):
        self.group = ' ' if self.type == 'singleChoice' else None
        line_of_code = self.code.count('\n')
        num_of_opts = len(self.options)
        power = 4 if line_of_code >= 8 and num_of_opts >= 4 else 2

        self.options_area = GridLayout(cols=1)
        for option in self.options:
            self.container = Factory.CheckBoxContainer()
            self.container.text = option
            self.container.group = self.group
            self.options_area.add_widget(self.container)

        self.root.ids.qstn_lbl.text = self.question
        self.root.ids.cd_lbl.text = self.code
        self.root.ids.opt_cntnr.add_widget(self.options_area)
        self.root.ids.opt_cntnr.add_widget(Label(size_hint=(1, (2 / num_of_opts) ** power)))

    def checkbox_checked(self, instance, value, name):
        if value:
            self.your_answer.append(name)
        elif name in self.your_answer:
            self.your_answer.remove(name)

    def dropdown_select(self):
        pass

    def rating(self):
        if len(self.selected_question) != 0:
            self.rate = len(self.your_answer) / len(self.correct_answer) if math.prod([int(i in self.correct_answer) for i in self.your_answer]) else 0
            self.score += self.rate
            if not int(self.rate):
                self.add_to_scroll()
            self.your_answer = []

    def add_to_scroll(self):
        scroll_container = Factory.DynamicGrid()

        your_answer = '[b]Your answer{}[/b]\n  {}'.format(self.is_are(len(self.your_answer) == 1), '\n  '.join(self.your_answer)) if self.your_answer else 'Missed'
        correct_answer = '[b]The correct answer{}[/b]\n  {}'.format(self.is_are(self.type == 'singleChoice'), '\n  '.join(self.correct_answer))

        top = f'{self.question}\n\n[size={int(sp(18))}]{self.code}[/size]' if self.code else self.question
        bottom = f'{your_answer}\n\n{correct_answer}'

        scroll_container.add_widget(Factory.SColoredDynamicLabel(text=top))
        scroll_container.add_widget(Factory.QColoredDynamicLabel(text=bottom))
        self.root.ids.scrll_grd.add_widget(scroll_container)

    def is_are(self, condition):
        return ' is:' if condition else 's are:'

    def score_report(self):
        Animation.cancel_all(self)
        time_taken = self.duration - self.timer
        grade = int(self.score / self.number_of_question * 100)

        self.root.ids.sm.transition.mode = 'push'
        self.root.ids.sm.transition.direction = 'up'
        self.root.ids.sm.current = 'report_screen'

        self.root.ids.tm_lbl.text = f'Time taken:\n[b]{int(time_taken // 60):02d}:{int(time_taken % 60):02d}[/b]' if self.timer else 'timeout'
        self.root.ids.num_lbl.text = f'Marks:\n[b]{round(self.score, 2) if self.score % 1 else int(self.score)}/{self.number_of_question}[/b]'
        self.root.ids.grd_lbl.text = f'{grade}%'
        self.root.ids.rslt_lbl.text = '[b][color=00ff00]PASS[/color][/b]' if grade >= 80 else '[b][color=ff0000]FAIL[/color][/b]'

    def on_start(self):
        self.statusbar()

    @run_on_ui_thread
    def statusbar(self):
        window = activity.getWindow()
        window.clearFlags(WindowManager.FLAG_TRANSLUCENT_STATUS)
        window.addFlags(WindowManager.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
        window.setStatusBarColor(Color.parseColor("#F2DCA5"))
        window.setNavigationBarColor(Color.parseColor("#243441"))


if __name__ == "__main__":
    PythonQuizApp().run()