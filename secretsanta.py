import pandas as pd
from twilio.rest import Client
import random
import giphy_client
from giphy_client.rest import ApiException
from pprint import pprint


########################
# SET CONSTANT VARIABLES
########################

santa_message = '''{0}, you have the pleasure of participating in this years friends' gift exchange! Santa has picked you to give a gift to {1}. Date of the Christmas party is TBD. Just make sure you don\'t fuck it up... Oh, and Merry Christmas!!! Ho Ho HO!!!'''

elf_message_1 = '''{0}, you have been chosen to be head elf for a gift exchange. Lucky You. Someone Trusts and/or loves you... Or has nobody else to turn to... lol... Anyways, here is a list of each person, their number and who they are assigned to give a gift. It\'s likely you wont be contacted but in the case that you are it is probably because someone fucked up and forgot who they have. Thanks for being loved!!! Oh, and Merry Christmas!!!'''

elf_message_2 = '''Anyways, here is their info and who has who, just in case:'''

TESTING = False  # When set to true, random seed is set to 7 and prints results for verification. When set to False new random seed is set and text messages are sent.

########################


##############################
# LOAD CONFIGURATION VARIABLES
##############################

# SET RANDOM SEED
if TESTING:
    random.seed(7)
else:
    random.seed(13)

# GET API INFO AND KEYS
config_info = pd.read_csv('api_config.csv')

ACCOUNT = config_info.loc[config_info['key'] == 'ACCOUNT']['value'].values[0]  # Twilio Account
AUTH = config_info.loc[config_info['key'] == 'AUTH']['value'].values[0]  # Twilio API Key
FROM = config_info.loc[config_info['key'] == 'FROM']['value'].values[0]  # Twilio Phone Number
GIPHY = config_info.loc[config_info['key'] == 'GIPHY']['value'].values[0]  # GIPHY API Key

# Configure Twilio Client
client = Client(ACCOUNT, AUTH)


##############################


##################
# HELPER FUNCTIONS
##################


def add_christmas_gify():
    return '{0}'.format(get_random_santa_gif())


def get_random_santa_gif(api_key=GIPHY, tag='christmas', rating='PG-13', fmt='json'):
    api_instance = giphy_client.DefaultApi()
    api_key = api_key
    tag = tag
    rating = rating
    fmt = fmt

    try:
        # Random Sticker Endpoint
        api_response = api_instance.gifs_random_get(api_key, tag=tag, rating=rating, fmt=fmt)
        return api_response.to_dict()['data']['image_original_url']
    except ApiException as e:
        print("Exception when calling DefaultApi->stickers_random_get: %s\n" % e)
        return None


def send_sms(body, test, TO, client=client, FROM=FROM, media=None):
    if test:
        print('MSG:', body)
        print('Number:', TO)
        print('Media:', media)

    else:
        client.messages.create(
            to=TO,
            from_=FROM,
            body=body,
            media_url=media)

##################


#############
# PICK SANTAS
#############

# Parse persons info
people_info = pd.read_csv('santas.csv', dtype={'number': 'str'})


santas_info = people_info.loc[people_info['type'] == 'Santa'][['name', 'number', 'relationship']]
## To-do Split relationships directly from csv. Auto-detect if relationships exist.
relationships = santas_info[~santas_info['relationship'].isnull()].set_index('name').to_dict()['relationship']
santas_info = santas_info[['name', 'number']].set_index('name').to_dict('index')
elf_info = people_info.loc[people_info['type'] != 'Santa'][['name', 'number']]

santas = list(santas_info.keys())
options = list(santas_info.keys())

random.shuffle(santas)
random.shuffle(options)


# Elegantly making it so you don't ever have to reshuffle.
# pick random relationship to set to first and second to last
coupled = random.choice(list(relationships.keys()))
# Set one member of the couple to be the very first of the santas
santas.insert(0, santas.pop(santas.index(coupled)))
# Move the other member of the relationship to be the second to last.
santas.insert(-1, santas.pop(santas.index(relationships[coupled])))
# Move the other member of the relationship to be the very first position of the options
options.insert(0, options.pop(options.index(relationships[coupled])))
# If the last santa is also in a relationship, make sure that that
if santas[-1] in relationships.keys():
    options.insert(0, options.pop(options.index(santas[-1])))
    options.insert(0, options.pop(options.index(relationships[options[0]])))

pairs = {}
for i, santa in enumerate(santas):
    if i == 0:
        gives_to = santas[-1]
        options.remove(santas[-1])
        pairs[santa] = gives_to

    else:
        bad_match = [santa]
        if santa in relationships.keys():
            bad_match.append(relationships[santa])
        if options[0] not in bad_match:
            gives_to = options[0]
        elif options[1] not in bad_match:
            gives_to = options[1]
        else:
            gives_to = options[2]

        options.remove(gives_to)
        pairs[santa] = gives_to

#############


###############
# SEND MESSAGES
###############

for pair in pairs:
    santas_info[pair]['gives to'] = pairs[pair]
    to_num = santas_info[pair]['number']
    msg = santa_message.format(pair, pairs[pair])
    send_sms(msg, TO=to_num, test=TESTING, media=add_christmas_gify())

send_sms(elf_message_1.format(elf_info.name.values[0]), TO=elf_info.number.values[0], test=TESTING, media=add_christmas_gify())

send_sms(elf_message_2 + '\n\n' + str(santas_info), TO=elf_info.number.values[0], test=TESTING)

#############
