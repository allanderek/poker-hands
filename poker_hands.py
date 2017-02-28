import jinja2
import csv

class PokerHand(object):
    def __init__(self):
        self.players = []
        self.events = []

    def calculate_hand(self):
        pass


class Player(object):
    """Note that this only represents a player during one hand."""
    def __init__(self, index):
        self.index = index
        self.hand_winner = False
        self.ending_stack = 0

class Event(object):
    def __init__(self, starting_time):
        self.starting_time = starting_time
        self.action = ""
        self.player = ""
        self.card = ""
        self.amount = 0

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

        if not player.name.startswith("SEAT"):
            hand.players.append(player)
            assert len(hand.players) == player_index
    events_starting_index = players_starting_index + 4 * number_of_players
    for event_start in range(events_starting_index, len(fields), 5):
        starting_time = fields[event_start]
        if not starting_time:
            continue
        event = Event(starting_time)
        event.action = fields[event_start + 1]
        assert event.action in ['BOARD', 'BET', 'CALL', 'FOLD']
        # The very last event is generally cut off at the point it has no more
        # information, and the last event is often a fold hence we just assume
        # if there is an index error then the rest of the fields are empty.
        try:
            event.player = fields[event_start + 2]
            event.card = fields[event_start + 3]
            amount_string = fields[event_start + 4]
            event.amount = 0 if not amount_string else int(amount_string)
        except IndexError:
            pass
        hand.events.append(event)

    hand.calculate_hand()
    print("completed hand")
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