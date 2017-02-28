import jinja2
import csv

class PokerHand(object):
    def __init__(self):
        self.players = []

class Player(object):
    def __init__(self, index):
        self.index = index

def parse_hand(fields):
    if not fields or fields[0].startswith("//"):
        return None
    hand = PokerHand()
    hand.starting_time = fields[0]
    hand.title = fields[1]
    title_fields = hand.title.split(' ')
    if title_fields[0] == 'Hand':
        hand.number = title_fields[1]
    
    hand.ante = fields[2]
    hand.small_blind = fields[3]
    hand.big_blind = fields[4]
    hand.dealer = fields[5]
    hand.small_blind_player = fields[6]
    hand.big_blind_player = fields[7]
    players_starting_index = 8
    number_of_players = 10
    for player_index in range(1,number_of_players + 1):
        start_index = players_starting_index + ((player_index - 1) * 4)
        player = Player(player_index)
        player.name = fields[start_index]
        player.straddle = fields[start_index + 1]
        player.cards = fields[start_index + 2]
        player.stack = fields[start_index + 3]
        
        hand.players.append(player)
        assert len(hand.players) == player_index
    return hand

def read_poker_datafile(filename):
    with open(filename, 'r') as input_file:
        csvreader = csv.reader(input_file, delimiter=',', quotechar='"')
        for row in csvreader:
            poker_hand = parse_hand(row)
            if poker_hand:
                yield poker_hand

def compile_poker_hands_html():
    env = jinja2.Environment(
        loader=jinja2.PackageLoader('poker_hands', '.'),
        autoescape=jinja2.select_autoescape(['html', 'xml'])
    )
    template = env.get_template('poker-hands.jinja')

    poker_hands = read_poker_datafile('example.csv')

    with open('poker-hands.html', 'w') as outfile:
        outfile.write(template.render(
            poker_hands=poker_hands
            ))
    print("Recompile complete.")

if __name__ == '__main__':
    compile_poker_hands_html()