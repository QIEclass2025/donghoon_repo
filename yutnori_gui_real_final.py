import tkinter as tk
from collections import defaultdict
import random

# ============ 1) 노드/좌표/ID 매핑 ============ 

NODE, ID2POS = {}, []
def nid(xy):
    if xy not in NODE:
        NODE[xy] = len(ID2POS)
        ID2POS.append(xy)
    return NODE[xy]

# 외곽(반시계 CCW) 20칸
outer = [
    (1,0),(1,0.2),(1,0.4),(1,0.6),(1,0.8),(1,1),
    (0.8,1),(0.6,1),(0.4,1),(0.2,1),(0,1),
    (0,0.8),(0,0.6),(0,0.4),(0,0.2),(0,0),
    (0.2,0),(0.4,0),(0.6,0),(0.8,0)
]
# 대각선: BL↔TR, TL↔BR
diag_bl_tr = [(0,0),(0.2,0.2),(0.4,0.4),(0.5,0.5),(0.6,0.6),(0.8,0.8),(1,1)]
diag_tl_br = [(0,1),(0.2,0.8),(0.4,0.6),(0.5,0.5),(0.6,0.4),(0.8,0.2),(1,0)]

OUT_IDS  = [nid(p) for p in outer]
BLTR_IDS = [nid(p) for p in diag_bl_tr]  # [BL(0),...,CENTER(3),...,TR(6)]
TLBR_IDS = [nid(p) for p in diag_tl_br]  # [TL(0),...,CENTER(3),...,BR(6)]

START_ID  = OUT_IDS[0]   # BR
TR_ID     = OUT_IDS[5]
TL_ID     = OUT_IDS[10]
BL_ID     = OUT_IDS[15]
CENTER_ID = nid((0.5,0.5))

# ============ 2) 이동 그래프(NEXTS) 구성 ============ 
# - 외곽: CCW 1칸씩
# - 지름길:
#   • TR쪽 내부: TR(6)→5→4→CENTER(3)
#   • TL쪽 내부: TL(0)→1→2→CENTER(3)
#   • CENTER 이후 반대 코너 쪽: BLTR 2→1→0, TLBR 4→5→6
#   • 입구(TR/TL)에 서 있으면 무조건 지름길로 진입(코드에서 강제)
NEXTS = defaultdict(list)
def add_edge(u, v):
    NEXTS[u].append(v)

# 외곽 CCW
for i, u in enumerate(OUT_IDS):
    add_edge(u, OUT_IDS[(i + 1) % len(OUT_IDS)])

# 대각선 내부(입구→센터) 방향
# BLTR: TR→...→CENTER (6→5→4→3)
for i in range(len(BLTR_IDS) - 1, 3, -1):   # 6,5,4
    add_edge(BLTR_IDS[i], BLTR_IDS[i - 1])
# TLBR: TL→...→CENTER (0→1→2→3)
for i in range(0, 3):                       # 0,1,2
    add_edge(TLBR_IDS[i], TLBR_IDS[i + 1])

# 대각선(센터 이후 반대 코너 방향) — 센터 자체에서의 엣지는 만들지 않음(센터는 코드로 분기)
# BLTR: 2→1→0 (CENTER(3) 뒤 BL 쪽)
for i in range(2, 0, -1):
    add_edge(BLTR_IDS[i], BLTR_IDS[i - 1])
# TLBR: 4→5→6 (CENTER(3) 뒤 BR 쪽)
for i in range(4, len(TLBR_IDS) - 1):
    add_edge(TLBR_IDS[i], TLBR_IDS[i + 1])

# ============ 3) 윷/말/게임 로직 ============ 

import urllib.request
import json

YUT_MAP = {"도": 1, "개": 2, "걸": 3, "윷": 4, "모": 5, "빽도": -1}
YUT_SYMBOL = {'flat': '▮', 'round': '▯', 'flat_x': '▮', 'round_x': 'X'}

def get_pokemon_data(english_name):
    try:
        # 1. Get main pokemon data (for species URL and sprite URL)
        with urllib.request.urlopen(f"https://pokeapi.co/api/v2/pokemon/{english_name.lower()}/", timeout=5) as url:
            main_data = json.loads(url.read().decode())
        
        species_url = main_data['species']['url']
        sprite_url = main_data['sprites']['front_default']

        # 2. Get species data (for Korean name)
        korean_name = english_name.capitalize() # Default to English name
        with urllib.request.urlopen(species_url, timeout=5) as url:
            species_data = json.loads(url.read().decode())
        
        for name_info in species_data['names']:
            if name_info['language']['name'] == 'ko':
                korean_name = name_info['name']
                break
        
        # 3. Get sprite data
        sprite_data = None
        if sprite_url:
            with urllib.request.urlopen(sprite_url, timeout=5) as url:
                sprite_data = url.read()

        return {'korean_name': korean_name, 'sprite_data': sprite_data}
    except Exception as e:
        print(f"Error getting pokemon data for {english_name}: {e}")
        return {'korean_name': english_name.capitalize(), 'sprite_data': None}


def get_advice():
    try:
        with urllib.request.urlopen("https://api.adviceslip.com/advice", timeout=5) as url:
            data = json.loads(url.read().decode())
            return data['slip']['advice']
    except Exception:
        return "승리한 당신, 언제나 최고입니다!" # Fallback advice

def throw_yut():
    sticks = [random.choice(['flat', 'round']) for _ in range(3)] + [random.choice(['flat_x', 'round_x'])]
    flat_count = sticks.count('flat') + sticks.count('flat_x')
    visuals = [YUT_SYMBOL[s] for s in sticks]
    if 'flat_x' in sticks and flat_count == 1:
        visuals[sticks.index('flat_x')] = 'X'
    if flat_count == 0: return '모', visuals
    if flat_count == 1: return ('빽도', visuals) if 'flat_x' in sticks else ('도', visuals)
    if flat_count == 2: return '개', visuals
    if flat_count == 3: return '걸', visuals
    if flat_count == 4: return '윷', visuals

class Piece:
    def __init__(self, pid, player_info, pokemon_name):
        self.id = pid
        self.player_info = player_info
        self.pokemon_name = pokemon_name # English name for API calls
        self.korean_name = pokemon_name.capitalize() # Default value
        self.sprite_image = None
        self.node_id = -1
        self.onBoard = False
        self.stacked_pieces = [self]
        self.history = []

    def is_waiting(self):  return not self.onBoard
    def is_finished(self): return self.node_id == -2

class YutnoriGameLogic:
    def __init__(self):
        p1_pokemon = ['squirtle', 'totodile', 'mudkip', 'piplup']
        p2_pokemon = ['charmander', 'cyndaquil', 'torchic', 'chimchar']

        self.players = [
            {'name': '플레이어 1', 'color': 'blue',
             'pieces': [Piece(i, {'name': '플레이어 1', 'color': 'blue'}, p1_pokemon[i-1]) for i in range(1, 5)]},
            {'name': '플레이어 2', 'color': 'red',
             'pieces': [Piece(i, {'name': '플레이어 2', 'color': 'red'}, p2_pokemon[i-1]) for i in range(1, 5)]}
        ]
        self.current_player_index = 0
        self.turn_moves = []

    def get_current_player(self): return self.players[self.current_player_index]
    def switch_player(self):      self.current_player_index = 1 - self.current_player_index
    def check_win_condition(self): return all(p.is_finished() for p in self.get_current_player()['pieces'])

    # --- 입장/후진 --- 
    def _enter_from_offboard(self, piece):
        piece.onBoard = True
        piece.node_id = START_ID
        piece.history = [START_ID]  # 출발칸은 0칸

    def _step_backward(self, piece):
        if not piece.onBoard:
            return
        if piece.node_id == START_ID:
            # 출발칸에서 빽도 → 오프보드로
            piece.onBoard = False
            piece.history = []
            piece.node_id = -1
            return
        if len(piece.history) >= 2:
            piece.history.pop()
            piece.node_id = piece.history[-1]

    # --- 핵심 이동 --- 
    def move_piece(self, piece, move_name):
        steps = YUT_MAP[move_name]
        is_starting_move = not piece.onBoard
        if is_starting_move:
            self._enter_from_offboard(piece)

        current_node = piece.node_id

        if steps == -1:
            self._step_backward(piece)
        else:
            # 이동 시작 전, 말이 지름길 입구에 있는지 확인
            is_on_tr_tl_entrance = piece.node_id in {TR_ID, TL_ID}
            is_on_center_entrance = piece.node_id == CENTER_ID

            for i in range(steps):
                # 현재 위치를 기준으로 다음 노드를 결정
                current_node = piece.node_id

                # 1) 턴 시작 시 TR/TL 입구에 있는 경우, 첫 스텝은 지름길로
                if i == 0 and is_on_tr_tl_entrance:
                    if current_node == TR_ID:
                        next_node = BLTR_IDS[-2]
                    else:  # TL_ID
                        next_node = TLBR_IDS[1]
                
                # 2) 턴 시작 시 중앙 입구에 있는 경우, 첫 스텝은 도착지로
                elif i == 0 and is_on_center_entrance:
                    next_node = TLBR_IDS[4]

                # 3) 이동 중 중앙을 통과하는 경우, 이전 경로에 따라 분기
                elif current_node == CENTER_ID:
                    if len(piece.history) < 2:
                        # 비정상적 경우, 안전하게 도착지 방향으로
                        next_node = TLBR_IDS[4]
                    else:
                        prev = piece.history[-2]
                        if prev in BLTR_IDS:  # TR -> BL 경로로 진행 중
                            next_node = BLTR_IDS[2]
                        elif prev in TLBR_IDS:  # TL -> BR 경로로 진행 중
                            next_node = TLBR_IDS[4]
                        else: # 외곽에서 들어온 비정상적 경우
                            next_node = TLBR_IDS[4]

                # 4) 일반 노드: NEXTS 그래프를 따라 이동
                else:
                    options = NEXTS.get(current_node, [])
                    if not options:
                        piece.node_id = -2  # 막다른 길 = 완주 또는 오류
                        break
                    next_node = options[0]

                # 상태 갱신
                piece.history.append(next_node)
                piece.node_id = next_node

                # 완주: 시작점을 지나치면(턴 시작이 아닌 상태에서 START 재도달)
                if piece.node_id == START_ID and not is_starting_move:
                    piece.node_id = -2
                    break

                if piece.is_finished():
                    break

        # 스택(업기) 동기화
        for p in piece.stacked_pieces:
            p.node_id = piece.node_id
            p.history = piece.history[:]
            p.onBoard = piece.onBoard

        if piece.is_finished():
            return {'captured': False}

        # 잡기 / 업기
        captured = False
        if piece.onBoard:
            # 상대 잡기
            for opp in self.players[1 - self.current_player_index]['pieces']:
                if opp.onBoard and opp.node_id == piece.node_id:
                    stacked_to_reset = list(opp.stacked_pieces)
                    for sp in stacked_to_reset:
                        sp.onBoard, sp.node_id, sp.history = False, -1, []
                        sp.stacked_pieces = [sp]
                    captured = True
            # 아군 업기
            for ally in self.get_current_player()['pieces']:
                if ally is not piece and ally.onBoard and ally.node_id == piece.node_id and ally not in piece.stacked_pieces:
                    merged = ally.stacked_pieces + piece.stacked_pieces
                    for sp in merged:
                        sp.stacked_pieces = merged
                    break

        return {'captured': captured}

# ============ 4) GUI ============ 

class YutnoriGUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title('윷놀이')
        self.master.geometry('1000x720')
        self.pack(fill=tk.BOTH, expand=True)

        self.game = YutnoriGameLogic()
        self.selected_piece = None
        self.canvas_size, self.margin = 560, 40

        self.create_widgets()
        self.load_all_pokemon_data() # Load sprites and names before first draw
        self.update_display()
        self.master.bind('<F1>', self.cheat_win_p1)

    def norm_to_canvas(self, pos):
        x = self.margin + pos[0] * self.canvas_size
        y = self.margin + (1 - pos[1]) * self.canvas_size
        return x, y

    def create_widgets(self):
        canvas_dim = self.canvas_size + 2 * self.margin
        self.canvas = tk.Canvas(self, width=canvas_dim, height=canvas_dim, bg='#D2B48C', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        control = tk.Frame(self, width=220, bg='#F0F0F0')
        control.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=10)
        control.pack_propagate(False)

        self.player_label = tk.Label(control, text="", font=("Malgun Gothic", 18, "bold"), bg='#F0F0F0', fg='#2244FF')
        self.player_label.pack(pady=(10, 10))

        self.yut_display_label = tk.Label(control, text="", font=("Malgun Gothic", 24, "bold"), bg='#F0F0F0', height=2)
        self.yut_display_label.pack(pady=10)

        self.throw_button = tk.Button(control, text="윷 굴리기", command=self.handle_throw_yut, height=2)
        self.throw_button.pack(pady=10, fill=tk.X, padx=12)

        self.moves_frame = tk.Frame(control, bg='#F0F0F0')
        self.moves_frame.pack(pady=10, fill=tk.X)

        self.message_label = tk.Label(control, text="게임을 시작하세요!", wraplength=180, bg='#F0F0F0',
                                      font=("Malgun Gothic", 10, "bold"), fg='#333')
        self.message_label.pack(side=tk.BOTTOM, pady=20)

    def draw_board(self):
        self.canvas.delete("board")
        # 외곽 선
        for i in range(len(outer)):
            self.canvas.create_line(
                self.norm_to_canvas(outer[i]),
                self.norm_to_canvas(outer[(i + 1) % len(outer)]),
                width=2, fill="#222", tags="board"
            )
        # 대각선 선(두 줄)
        self.canvas.create_line(self.norm_to_canvas(diag_bl_tr[0]), self.norm_to_canvas(diag_bl_tr[-1]),
                                width=2, fill="#222", tags="board")
        self.canvas.create_line(self.norm_to_canvas(diag_tl_br[0]), self.norm_to_canvas(diag_tl_br[-1]),
                                width=2, fill="#222", tags="board")

        # 노드 원
        for i, pos in enumerate(ID2POS):
            x, y = self.norm_to_canvas(pos)
            is_corner = i in (START_ID, TR_ID, TL_ID, BL_ID)
            is_center = i == CENTER_ID
            r = 16 if (is_corner or is_center) else 11
            fill = "#FFD000" if is_center else "white"
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline="#000", width=2, tags="board")

    def load_all_pokemon_data(self):
        self.message_label.config(text="포켓몬을 불러오는 중...")
        self.update()
        for player in self.game.players:
            for piece in player['pieces']:
                data = get_pokemon_data(piece.pokemon_name)
                piece.korean_name = data['korean_name']
                if data['sprite_data']:
                    piece.sprite_image = tk.PhotoImage(data=data['sprite_data'])
        self.message_label.config(text="게임을 시작하세요!")

    def draw_pieces(self):
        self.canvas.delete("piece")
        for pidx, player in enumerate(self.game.players):
            color = player['color']
            for idx, piece in enumerate(player['pieces']):
                tag = f"p{pidx}_m{piece.id}"

                if piece.is_waiting():
                    if pidx == 0:  # Player 1 on the left
                        base = (0.04, -0.10)
                        offset_x = base[0] + 0.08 * (idx % 4)
                        x, y = self.norm_to_canvas((offset_x, base[1]))
                    else:  # Player 2 on the right
                        base = (0.96, -0.10)
                        offset_x = base[0] - 0.08 * (idx % 4)
                        x, y = self.norm_to_canvas((offset_x, base[1]))

                    if piece.sprite_image:
                        self.canvas.create_image(x, y, image=piece.sprite_image, tags=("piece", tag))
                    else: # Fallback
                        self.canvas.create_oval(x-12, y-12, x+12, y+12, fill=color, outline="", tags=("piece", tag))
                        self.canvas.create_text(x, y, text=str(piece.id), fill="white", tags=("piece", tag))
                    self.canvas.tag_bind(tag, "<Button-1>", lambda e, p=piece: self.handle_piece_click(p))
                    continue

                if piece.is_finished():
                    # 완주 표시는 텍스트로 유지
                    self.canvas.create_text(690, 60 + pidx*120 + idx*25,
                                            text=f"- {piece.korean_name}", fill=player['color'], tags="piece", anchor="w")
                    continue

                # 스택이면 맨 아래 말만 그림
                if len(piece.stacked_pieces) > 1 and piece is not piece.stacked_pieces[0]:
                    continue
                
                # Reverted on-board alignment to pixel offset
                cx, cy = self.norm_to_canvas(ID2POS[piece.node_id])
                ox = -20 if pidx == 0 else 20
                x, y = cx + ox, cy

                if piece.sprite_image:
                    self.canvas.create_image(x, y, image=piece.sprite_image, tags=("piece", tag))
                else: # Fallback
                    self.canvas.create_oval(x-12, y-12, x+12, y+12, fill=color, outline="", tags=("piece", tag))
                    self.canvas.create_text(x, y, text=str(piece.id), fill="white", tags=("piece", tag))

                if len(piece.stacked_pieces) > 1:
                    self.canvas.create_text(x, y + 20, text=f"+{len(piece.stacked_pieces)-1}", fill=color,
                                            font=("Malgun Gothic", 10, "bold"), tags=("piece", tag))
                self.canvas.tag_bind(tag, "<Button-1>", lambda e, p=piece: self.handle_piece_click(p))

    def update_display(self):
        self.draw_board()
        self.draw_pieces()
        cur = self.game.get_current_player()
        self.player_label.config(text=cur['name'], fg=cur['color'])
        self.update_moves_display()

    def update_moves_display(self):
        for w in self.moves_frame.winfo_children():
            w.destroy()

        can_move_backdo = any(p.onBoard for p in self.game.get_current_player()['pieces'])
        
        if not self.game.turn_moves:
            tk.Label(self.moves_frame, text="이동할 결과가 없습니다.", bg="#F0F0F0").pack()
            return

        has_playable_moves = False
        playable_moves_frame = tk.Frame(self.moves_frame, bg='#F0F0F0')
        
        for mv in self.game.turn_moves:
            if mv == '빽도' and not can_move_backdo:
                continue
            
            has_playable_moves = True
            tk.Button(playable_moves_frame, text=f"{mv}({YUT_MAP[mv]})",
                      command=lambda m=mv: self.handle_move_selection(m)).pack(fill=tk.X, padx=10, pady=2)

        if not has_playable_moves:
            tk.Label(self.moves_frame, text="움직일 수 있는 말이 없습니다.", bg="#F0F0F0").pack()
            tk.Button(self.moves_frame, text="턴 넘기기",
                      command=self.handle_pass_turn).pack(fill=tk.X, padx=10, pady=2)
        else:
            tk.Label(self.moves_frame, text="사용할 이동 선택:", bg="#F0F0F0").pack()
            playable_moves_frame.pack(fill=tk.X)

    def handle_pass_turn(self):
        self.message_label.config(text="턴 종료. 다음 플레이어 차례입니다.")
        self.game.turn_moves = []
        self.game.switch_player()
        self.throw_button.config(state=tk.NORMAL)
        self.update_display()

    # -------- 컨트롤러 -------- 
    def handle_throw_yut(self):
        self.throw_button.config(state=tk.DISABLED)
        name, visuals = throw_yut()
        self.show_yut_animation(name, visuals)

    def show_yut_animation(self, final_name, final_visuals):
        animation_duration = 1000  # 1 second for animation
        
        start_time = self.master.winfo_toplevel().tk.call('clock', 'milliseconds')

        def animate():
            elapsed = self.master.winfo_toplevel().tk.call('clock', 'milliseconds') - start_time
            if elapsed < animation_duration:
                # Animate with symbols
                sticks = [random.choice(['flat', 'round']) for _ in range(3)] + [random.choice(['flat_x', 'round_x'])]
                visuals = [YUT_SYMBOL[s] for s in sticks]
                visual_str = " ".join(visuals)
                self.yut_display_label.config(text=f"{visual_str}")
                self.master.after(50, animate)
            else:
                # Show final result
                visual_str = " ".join(final_visuals)
                self.yut_display_label.config(text=f"{final_name}\n{visual_str}")
                self.after_animation(final_name)

        animate()

    def after_animation(self, name):
        # 빽도인데 판에 말이 없는 경우
        if name == '빽도' and not any(p.onBoard for p in self.game.get_current_player()['pieces']):
            self.message_label.config(text="빽도! 하지만 움직일 말이 없어 턴을 넘깁니다.")
            self.game.switch_player()
            self.update_display()
            self.throw_button.config(state=tk.NORMAL)
            return

        self.game.turn_moves.append(name)
        self.update_moves_display()
        
        if name in ('윷', '모'):
            self.throw_button.config(state=tk.NORMAL)
        
        self.message_label.config(text="움직일 말을 클릭하세요.")

    def handle_piece_click(self, piece):
        if piece.player_info['name'] != self.game.get_current_player()['name']:
            return
        if not self.game.turn_moves:
            return
        self.selected_piece = piece
        self.message_label.config(text=f"{piece.korean_name}({piece.id}번 말) 선택됨.")

    def handle_move_selection(self, move_name):
        if not self.selected_piece:
            self.message_label.config(text="먼저 움직일 말을 클릭하세요.")
            return
        if move_name not in self.game.turn_moves:
            return

        # 빽도 꼼수 방지
        if self.selected_piece.is_waiting() and move_name == '빽도':
            self.message_label.config(text="판에 없는 말은 빽도를 할 수 없습니다.")
            return

        result = self.game.move_piece(self.selected_piece, move_name)
        self.game.turn_moves.remove(move_name)
        self.selected_piece = None

        extra = (move_name in ('윷', '모')) or result.get('captured', False)
        if extra:
            self.message_label.config(text="한 번 더 굴립니다!")
            self.throw_button.config(state=tk.NORMAL)

        if self.game.check_win_condition():
            self.end_game()
            return

        self.update_display()

        if not self.game.turn_moves and not extra:
            self.message_label.config(text="턴 종료. 다음 플레이어 차례입니다.")
            self.game.switch_player()
            self.throw_button.config(state=tk.NORMAL)
            self.update_display()

    def end_game(self):
        w = self.game.get_current_player()
        advice = get_advice()
        win_message = f"게임 종료! {w['name']} 승리!\n\n{advice}"
        self.message_label.config(text=win_message)
        self.throw_button.config(state=tk.DISABLED)

    def cheat_win_p1(self, event=None):
        """Cheat function to make Player 1 win instantly."""
        self.game.current_player_index = 0
        player1_pieces = self.game.players[0]['pieces']
        for piece in player1_pieces:
            piece.node_id = -2  # Set as finished
        self.update_display()
        self.end_game()

# ============ 5) 실행 ============ 

if __name__ == "__main__":
    root = tk.Tk()
    app = YutnoriGUI(master=root)
    app.mainloop()
