import csv
import enum
from collections import defaultdict
import itertools
import traceback
import datetime

import jinja2

def parse_card(card):
    suit = card[-1]
    value = card[:-1]
    # Note, ace is ranked as 14 because for things such as high-card we will
    # want to sort it in that manner. However, for straights we have to be
    # careful to include a,2,3,4,5.
    value = {'a': 14,
             'j': 11,
             'q': 12,
             'k': 13}.get(value, None) or int(value)
    return value, suit

def new_deck():
    return [(value, suit) for value in range(2,15) for suit in ['c', 'h', 'd', 's']]

def parse_pocket(pocket):
    if not pocket.strip():
        return []
    return [parse_card(c) for c in pocket.strip().split(' ')]

class HandClass(enum.IntEnum):
    # A player may not be obliged to display their cards at the showdown, but
    # that means that they have lost the hand, hence we rank a 'not-shown' as
    # the worst possible hand.
    not_shown = 0
    high_card = 1
    pair = 2
    two_pair = 3
    three_of_a_kind = 4
    straight = 5
    flush = 6
    full_house = 7
    four_of_a_kind = 8
    straight_flush = 9

class HandRank(object):
    def __init__(self, rank, value_counts):
        self.rank = rank
        # The self.values is tricky to get correct. We want to be able to compare
        # hands simply by comparing their rank and if those are the same then
        # compare their values. However we need to first compare the ranks of
        # the cards of which are there most, for example we want a full house of
        # 6s over 2s to beat a full house of 3s over 10s. However, we also need
        # to sort over rank since we want a two pair 8s over 4s to beat two pair
        # 7s over 5s. So the below will make sure that a full house of 3s over 10s
        # is represented as:
        # [(3, 3), (2, 10), (1, 8)] and 6s over 2s is represented as
        # [(3, 6), (2, 2), (1,8)] because (3,6) is more than (3,3) the second
        # hand wins. Simliarly 88,44,2 will beat 77,55,2 because their representations
        # will be:
        # [(2,8), (2,4), (1,2)]
        # [(2,7), (2,5), (1,2)]
        # Note that it is important that we sort first by count, but *then* by
        # value, since if we did not we might end up with:
        # [(2,4), (2,8), (1,2)] for the first hand which would *compare* lower
        # than the second.
        self.card_values = sorted([(count, rank) for rank, count in value_counts.items()], reverse=True)

    def __eq__(self, other):
        return (self.rank, self.card_values) == (other.rank, other.card_values)

    def __le__(self, other):
        return (self.rank, self.card_values) <= (other.rank, other.card_values)

    def __lt__(self, other):
        return (self.rank, self.card_values) < (other.rank, other.card_values)


def best_hand(pocket, flop):
    def get_value_counts(cards):
        value_counts = defaultdict(int)
        for value, _suit in cards:
            value_counts[value] += 1
        return value_counts

    if len(pocket) != 2:
        print(flop)
        return HandRank(HandClass.not_shown, get_value_counts(flop))
    assert len(flop) == 5

    possible_hands = [
        # Using no pocket cards
        [flop[0], flop[1], flop[2], flop[3], flop[4]],
        # Using first pocket card,
        [pocket[0], flop[0], flop[1], flop[2], flop[3]],
        [pocket[0], flop[0], flop[1], flop[2], flop[4]],
        [pocket[0], flop[0], flop[1], flop[3], flop[4]],
        [pocket[0], flop[0], flop[2], flop[3], flop[4]],
        [pocket[0], flop[1], flop[2], flop[3], flop[4]],
        # Using the second pocket card
        [pocket[1], flop[0], flop[1], flop[2], flop[3]],
        [pocket[1], flop[0], flop[1], flop[2], flop[4]],
        [pocket[1], flop[0], flop[1], flop[3], flop[4]],
        [pocket[1], flop[0], flop[2], flop[3], flop[4]],
        [pocket[1], flop[1], flop[2], flop[3], flop[4]],

        # Using both pocket cards
        [pocket[0], pocket[1], flop[0], flop[1], flop[2]],
        [pocket[0], pocket[1], flop[0], flop[1], flop[3]],
        [pocket[0], pocket[1], flop[0], flop[2], flop[3]],
        [pocket[0], pocket[1], flop[1], flop[2], flop[3]],

        [pocket[0], pocket[1], flop[0], flop[1], flop[4]],
        [pocket[0], pocket[1], flop[0], flop[2], flop[4]],
        [pocket[0], pocket[1], flop[1], flop[2], flop[4]],

        [pocket[0], pocket[1], flop[0], flop[3], flop[4]],
        [pocket[0], pocket[1], flop[1], flop[3], flop[4]],

        [pocket[0], pocket[1], flop[2], flop[3], flop[4]],
        ]

    def hand_rank(cards):
        suits = set([suit for _v, suit in cards])
        flush = len(suits) == 1
        values = [value for value, _s in cards]
        straight = False
        for start in range(2, 11):
            if all(i in values for i in range(start, start+5)):
                straight = True
                break
        else:
            straight = all(i in values for i in [14, 2, 3, 4, 5])

        value_counts = get_value_counts(cards)

        if flush and straight:
            return HandRank(HandClass.straight_flush, value_counts)

        card_counts = value_counts.values()
        if 4 in card_counts:
            return HandRank(HandClass.four_of_a_kind, value_counts)

        if 3 in card_counts and 2 in card_counts:
            return HandRank(HandClass.full_house, value_counts)

        if flush:
            return HandRank(HandClass.flush, value_counts)

        if straight:
            return HandRank(HandClass.straight, value_counts)

        if 3 in card_counts:
            return HandRank(HandClass.three_of_a_kind, value_counts)

        if list(card_counts).count(2) == 2:
            return HandRank(HandClass.pair, value_counts)

        if 2 in card_counts:
            return HandRank(HandClass.pair, value_counts)

        return HandRank(HandClass.high_card, value_counts)

    return max([hand_rank(h) for h in possible_hands])




class PokerHand(object):
    def __init__(self):
        self.players = []
        self.events = []
        self.flop = []
        self.errors = []

    def get_player(self, player_index):
        player = self.players[player_index - 1] if player_index else None
        assert player is None or player.index == player_index
        return player

    @property
    def ending_time(self):
        return self.events[-1].starting_time

    @property
    def duration(self):
        shour, sminute, ssecond = [int(t) for t in self.starting_time.split(':')]
        ehour, eminute, esecond = [int(t) for t in self.ending_time.split(':')]
        hours = ehour - shour
        minutes = eminute - sminute
        seconds = esecond - ssecond
        while seconds < 0:
            seconds += 60
            minutes -= 1
        while minutes < 0:
            minutes += 60
            hours -= 1
        assert hours >= 0
        assert minutes >= 0
        assert seconds >= 0
        return "{0:2d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)

    @property
    def has_flop(self):
        return len(self.flop) >= 3

    @property
    def has_turn(self):
        return len(self.flop) >= 4

    @property
    def has_river(self):
        return len(self.flop) == 5

    @property
    def empty_seats(self):
        return range(len(self.players) + 1, 11)

    def calculate_winners(self, players, board):
        if len(players) == 1:
            return players
        for player in players:
            player.best_hand_rank = best_hand(player.pocket, board)
        winner = players[0]
        winners = [winner]
        for player in players[1:]:
            if winner.best_hand_rank < player.best_hand_rank:
                winner = player
                winners = [player]
            elif winner.best_hand_rank == player.best_hand_rank:
                winners.append(player)
        return winners

    def calculate_probabilities(self, players):
        # Don't bother attempting to calculate the probabilities for any players
        # that ultimately do not show their hand, this is unfortunate, but just
        # missing data and nothing we can do about it.
        players = [p for p in players if p.pocket]
        if len(self.flop) < 3:
            return None
        if not players:
            return {}
        if len(players) == 1:
            return { players[0].index: 100.0 }

        deck = new_deck()
        for card in self.flop:
            deck.remove(card)
        for player in players:
            for card in player.pocket:
                deck.remove(card)

        possible_draws = itertools.combinations(deck, 5 - len(self.flop))
        win_count = defaultdict(int)
        number_draws = 0
        for draw in possible_draws:
            number_draws += 1
            board = self.flop + list(draw)
            for winner in self.calculate_winners(players, board):
                win_count[winner] += 1

        def get_percentage(n):
            return 100 * n / number_draws
        return { player.index: get_percentage(win_count[player]) for player in players}

    def get_remaining_players(self):
        return [p for p in self.taking_part if not p.folded]

    def calculate_hand(self):
        pot = 0

        pot += self.big_blind + self.small_blind
        sb_player = self.get_player(self.small_blind_player)
        sb_player.ending_stack -= self.small_blind
        bb_player = self.get_player(self.big_blind_player)
        bb_player.ending_stack -= self.big_blind

        for player in self.players:
            pot += player.straddle
            player.ending_stack -= player.straddle

        # The list of player indexes that have made *some* action in the hand.
        event_players = set(e.player for e in self.events)
        # Some hands the big blind player wins without taking any action.
        event_players.add(self.big_blind_player)
        self.taking_part = [p for p in self.players if p.index in event_players]
        for p in self.taking_part:
            # Just a sanity check that no empty seats take part.
            assert not p.is_empty_seat
        # Also check that any player not taking part did not receive cards
        for p in self.players:
            if p not in self.taking_part:
                assert not p.cards

        most_recent_win_probabilities = None
        for event in self.events:
            player = self.get_player(event.player)
            player_description = "{} ({})".format(player.name, player.index) if player else None
            if event.action == 'BOARD':
                event.bold = True
                self.flop.append(parse_card(event.card))
                num_table_cards = len(self.flop)
                if num_table_cards < 3:
                    event.display = False
                elif num_table_cards == 3:
                    event.description = 'Flop'
                elif num_table_cards == 4:
                    event.description = "Turn"
                else:
                    assert num_table_cards == 5
                    event.description = "River"
            elif event.action == 'BET' and not event.amount:
                event.description = '{} Check'.format(player_description)
            elif event.action == 'BET':
                pot += event.amount
                player.ending_stack -= event.amount
                event.description = '{} Raise {}'.format(player_description, event.amount)
                event.bold = True
            elif event.action == 'ALL_IN':
                amount = player.ending_stack
                total_players_pot = amount + player.invested_in_hand
                if event.amount != player.ending_stack:
                    self.errors.append("All-in amount: {} not equal to the player's current stack {}".format(event.amount, player.ending_stack))
                pot += amount
                player.ending_stack = 0
                event.description = '{} goes all in for: {}'.format(player_description, amount)
                event.bold = True
            elif event.action == 'CALL':
                price = max(p.invested_in_hand for p in self.players)
                call_amount = price - player.invested_in_hand

                # TODO: In the case that it is more, then you end up with a side-pot
                # I think we can implement that relatively easily, by simply post-calculating
                # the amount each winner gets at the end of the hand, though of course
                # the winners would be calculated differently to now.
                assert call_amount <= player.ending_stack
                pot += call_amount
                player.ending_stack -= call_amount
                event.description = '{} Call {}'.format(player_description, call_amount)
            else:
                assert event.action == 'FOLD'
                player.folded = True
                event.description = '{} Fold'.format(player_description)
            # Careful, this applies to all events, but must be done after we have
            # potentially updated the pot.
            event.pot = pot
            # After we have taken the action of the event we re-calculate the
            # win probabilities, but for bet/calls (and all_ins) we know that
            # the probabilities will not have changed.
            if event.action in ['BET', 'CALL', 'ALL_IN']:
                event.win_probabilities = most_recent_win_probabilities
            else:
                remaining_players = self.get_remaining_players()
                event.win_probabilities = self.calculate_probabilities(remaining_players)
                most_recent_win_probabilities = event.win_probabilities
        # End of event stream.

        # It should not really be possible that this has not already been called
        # since we should have had at least one FOLD or BOARD event.
        # remaining_players = self.get_remaining_players()
        if len(remaining_players) == 1:
            winner = remaining_players[0]
            winners = [winner]
        else:
            assert len(remaining_players) > 1
            winners = self.calculate_winners(remaining_players, self.flop)

        winning_amount = pot / len(winners)
        for winner in winners:
            winner.hand_winner = True
            winner.ending_stack += winning_amount

class Player(object):
    """Note that this only represents a player during one hand."""
    def __init__(self, index):
        self.index = index
        self.hand_winner = False
        self.folded = False

    def init_stack(self, stack):
        self.starting_stack = stack
        # The ending stack will be updated in the Hand.calculate_hand method.
        self.ending_stack = stack

    @property
    def is_empty_seat(self):
        return self.name.startswith("SEAT")

    @property
    def has_pocket(self):
        return len(self.pocket)

    @property
    def invested_in_hand(self):
        return self.starting_stack - self.ending_stack


class Event(object):
    def __init__(self, starting_time):
        self.starting_time = starting_time
        self.action = ""
        self.player = ""
        self.card = ""
        self.amount = 0
        self.display = True
        self.bold = False
        self.win_probabilities = None

    def max_probability(self):
        return max(self.win_probabilities.values())

def parse_int(s):
    if not s:
        return None
    return int(s)

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
    hand.small_blind = parse_int(fields[3])
    hand.big_blind = parse_int(fields[4])
    hand.dealer = parse_int(fields[5])
    hand.small_blind_player = parse_int(fields[6])
    hand.big_blind_player = parse_int(fields[7])
    players_starting_index = 8
    number_of_players = 10
    for player_index in range(1,number_of_players + 1):
        start_index = players_starting_index + ((player_index - 1) * 4)
        player = Player(player_index)
        player.name = fields[start_index]
        player.straddle = parse_int(fields[start_index + 1])
        player.cards = fields[start_index + 2]
        player.pocket = parse_pocket(player.cards)
        player.init_stack(int(fields[start_index + 3]))

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

        assert event.action in ['BOARD', 'BET', 'CALL', 'FOLD', 'ALL_IN']
        # The very last event is generally cut off at the point it has no more
        # information, and the last event is often a fold hence we just assume
        # if there is an index error then the rest of the fields are empty.
        try:
            event.player = parse_int(fields[event_start + 2])
            event.card = fields[event_start + 3]
            event.amount = parse_int(fields[event_start + 4])
        except IndexError:
            pass
        hand.events.append(event)

    try:
        hand.calculate_hand()
    except Exception as error:
        print("Error in hand {}: {}".format(hand.number, error))
        hand.errors.append("Some irregularity in this hand's data was detected.")
        traceback.print_exc()
    return hand

def read_poker_datafile(filename):
    with open(filename, 'r') as input_file:
        csvreader = csv.reader(input_file, delimiter=',', quotechar='"')
        for row in csvreader:
            poker_hand = parse_hand(row)
            if poker_hand:
                yield poker_hand

def compile_poker_hands_html(input_filename, output_filename):
    print("Recompile commencing.")
    env = jinja2.Environment(
        loader=jinja2.PackageLoader('poker_hands', '.'),
        autoescape=jinja2.select_autoescape(['html', 'xml'])
    )
    template = env.get_template('poker-hands.jinja')

    poker_hands = read_poker_datafile(input_filename)


    with open(output_filename, 'w') as outfile:
        outfile.write(template.render(
            poker_hands=poker_hands,
            input_filename=input_filename,
            date=datetime.date.today()
            ))
    print("Recompile complete.")

import sys

def get_argument(index, default):
    if len(sys.argv) > index:
        return sys.argv[index]
    return default

if __name__ == '__main__':
    input_filename = get_argument(1, 'example.csv')
    output_filename = get_argument(2, 'poker-hands.html')
    compile_poker_hands_html(input_filename, output_filename)