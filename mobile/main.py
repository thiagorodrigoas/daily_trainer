from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.app import App

from kivymd.app import MDApp
from kivymd.uix.list import TwoLineListItem, ThreeLineListItem
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase
from kivy.properties import StringProperty

from api import list_alunos, list_treinos, list_exercicios, dashboard_summary


class TabAlunos(MDFloatLayout, MDTabsBase):
    text = StringProperty("Alunos")
    icon = StringProperty("account-group")


class TabTreinos(MDFloatLayout, MDTabsBase):
    text = StringProperty("Treinos")
    icon = StringProperty("dumbbell")


class TabExercicios(MDFloatLayout, MDTabsBase):
    text = StringProperty("Exercícios")
    icon = StringProperty("arm-flex")


class TabDashboard(MDFloatLayout, MDTabsBase):
    text = StringProperty("Painel")
    icon = StringProperty("view-dashboard")


class DailyTrainerApp(MDApp):
    def build(self):
        # Desktop default size for dev
        if platform in ("win", "linux", "macosx"):
            Window.size = (420, 760)
        return Builder.load_file("main.kv")

    def on_start(self):
        # Load initial data
        Clock.schedule_once(lambda dt: self.load_dashboard())
        Clock.schedule_once(lambda dt: self.load_alunos())
        Clock.schedule_once(lambda dt: self.load_treinos())
        Clock.schedule_once(lambda dt: self.load_exercicios())

    def on_tab_switch(self, *args):
        # Placeholder if we want to lazy load on tab change
        pass

    def show_error(self, msg):
        Snackbar(text=msg, duration=3).open()

    def load_dashboard(self):
        dash_sem = self.root.ids.dash_tab.ids.dash_sem_treino
        dash_treinos = self.root.ids.dash_tab.ids.dash_treinos
        dash_sem.clear_widgets()
        dash_treinos.clear_widgets()
        try:
            alunos_sem, treinos_resumo = dashboard_summary()
        except Exception as e:
            self.show_error(f"Erro ao carregar painel: {e}")
            return

        for a in alunos_sem:
            item = TwoLineListItem(
                text=f"{a.nome} (ID {a.id})",
                secondary_text=f"Turma: {a.turma or '-'} | Genero: {a.genero}",
            )
            dash_sem.add_widget(item)

        for t in treinos_resumo:
            grupos = ", ".join(t.get("grupos") or [])
            item = ThreeLineListItem(
                text=f"Aluno ID {t.get('aluno_id')} - Data: {t.get('data')}",
                secondary_text=f"Grupos: {grupos or '-'}",
                tertiary_text=f"Treino ID #{t.get('treino_id')}",
            )
            dash_treinos.add_widget(item)

    def load_alunos(self):
        alunos_list = self.root.ids.alunos_tab.ids.alunos_list
        alunos_list.clear_widgets()
        try:
            data = list_alunos()
        except Exception as e:
            self.show_error(f"Erro ao carregar alunos: {e}")
            return
        for aluno in data:
            aluno = dict(aluno)
            item = TwoLineListItem(
                text=f"{aluno.get('nome', 'Sem nome')} (ID {aluno.get('id')})",
                secondary_text=f"Genero: {aluno.get('genero','-')} | Turma: {aluno.get('turma') or '-'}",
            )
            alunos_list.add_widget(item)

    def load_treinos(self):
        treinos_list = self.root.ids.treinos_tab.ids.treinos_list
        treinos_list.clear_widgets()
        try:
            data = list_treinos()
        except Exception as e:
            self.show_error(f"Erro ao carregar treinos: {e}")
            return
        for treino in data:
            treino = dict(treino)
            item = ThreeLineListItem(
                text=f"Treino #{treino.get('id')}",
                secondary_text=f"Aluno ID: {treino.get('aluno_id')} | Data: {treino.get('data')}",
                tertiary_text=f"Obs: {treino.get('observacoes') or '-'}",
            )
            treinos_list.add_widget(item)

    def load_exercicios(self):
        exercicios_list = self.root.ids.exercicios_tab.ids.exercicios_list
        exercicios_list.clear_widgets()
        try:
            data = list_exercicios()
        except Exception as e:
            self.show_error(f"Erro ao carregar exercícios: {e}")
            return
        for ex in data:
            ex = dict(ex)
            item = ThreeLineListItem(
                text=f"{ex.get('nome')} (ID {ex.get('id')})",
                secondary_text=f"Grupo: {ex.get('grupo_muscular') or '-'} | Público: {ex.get('publico_alvo')}",
                tertiary_text=f"Padrão: {'Sim' if ex.get('padrao') else 'Não'} | {ex.get('series_padrao')}x{ex.get('repeticoes_padrao')}",
            )
            exercicios_list.add_widget(item)


if __name__ == "__main__":
    DailyTrainerApp().run()
