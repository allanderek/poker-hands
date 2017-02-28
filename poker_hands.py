import jinja2


class PokerHand(object):
    starting_time = 'Now'

def parse_hand(line):
    if line.startswith("//"):
        return None
    fields = line.split(",")
    hand = PokerHand()
    hand.starting_time = fields[0]
    return hand

def read_poker_datafile(filename):
    with open(filename, 'r') as input_file:
        for line in input_file:
            poker_hand = parse_hand(line)
            if poker_hand:
                yield poker_hand


if __name__ == '__main__':
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
