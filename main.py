import json
import os
from datetime import datetime

import discord


class SimpleClass:
    def __init__(self, **kwargs):
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])


class MessageTemplate:
    def __init__(self):
        with open('./messages.json', 'r', encoding='UTF-8') as fin:
            data = json.load(fin)
            self.messages = data['messages']
            self.statues_msg = data['status_msg']

    def get_template(self, kw):
        return self.messages[kw]

    def get_timestamp(self):
        return self.get_strftime(self.get_template('ts_format'))

    def get_strftime(self, ts_format):
        return datetime.now().strftime(ts_format)

    def set_timestamp(self, msg):
        sc = SimpleClass(ts=self.get_timestamp(), msg=msg)
        return self.get_template('ts').format(sc)

    def get_message(self, kw, *args):
        return self.get_template(kw).format(*args)

MT = MessageTemplate()


class VoiceState:
    def __init__(self, name, before, after):
        self.name = name
        self.name = MT.get_message('name', self)
        self.before = before
        self.after = after

    def get_message(self):
        for state in MT.statues_msg:
            if self.is_state_different(state):
                return self.get_message_log(state)
        return None

    def is_state_different(self, state):
        return getattr(self.before, state) != getattr(self.after, state)

    def get_message_log(self, state):
        # Change boolean to string, e.g. True -> "True"
        attr = str(getattr(self.after, state))
        state = MT.statues_msg[state][attr]
        sc = SimpleClass(name=self.name, state=state)
        msg = MT.get_message('state', sc)
        msg = MT.set_timestamp(msg)
        return msg


class ChannelState:
    def __init__(self, name, before, after):
        self.name = name
        self.name = MT.get_message('name', self)
        self.before = getattr(before.channel, 'name', None)
        self.after = getattr(after.channel, 'name', None)

    def get_message(self):
        if self.before is None:
            return self.get_message_log('join')

        if self.after is None:
            return self.get_message_log('leave')

        return self.get_message_log('move')

    def get_message_log(self, key):
        msg = MT.get_message(key, self)
        msg = MT.set_timestamp(msg)
        return msg


class VoiceLogger(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = self.load_config()
        self.log_channels = self.load_channels()
        self.init_command_map()

    def load_config(self):
        with open('./config.json', 'r', encoding='UTF-8') as fin:
            return json.load(fin)

    def load_channels(self):
        if os.path.exists('./channels.json'):
            with open('./channels.json', 'r') as fin:
                return json.load(fin)

        return dict()

    def init_command_map(self):
        self.cmd_map = dict()
        cmd_kw = [
            ('set_cmd', self.on_set_command),
            ('cls_cmd', self.on_cls_command),
            ('shutdown_cmd', self.on_shutdown_command)
        ]
        for kw, cmd in cmd_kw:
            self.cmd_map[self.config[kw]] = cmd

    async def on_ready(self):
        print(MT.get_message('login', self))

    async def on_message(self, message):
        if message.author == self.user:
            return
        cid = message.channel.id
        gid = str(message.guild.id)
        cmd = message.content.rstrip()
        await self.cmd_map.get(cmd, self.on_no_command)(message, gid, cid)

    async def on_set_command(self, message, gid, cid):
        self.log_channels[gid] = cid
        self.save()
        msg = MT.get_message('set', message)
        await message.channel.send(msg)

    async def on_cls_command(self, message, gid, cid):
        if self.log_channels.get(gid, None) is not None:
            del self.log_channels[gid]
        self.save()
        msg = MT.get_message('cls', message)
        await message.channel.send(msg)

    async def on_shutdown_command(self, message, *args):
        if message.author.id != self.config['author']:
            msg = MT.get_message('cant_shutdown')
            await message.channel.send(msg)
            return

        msg = MT.get_message('shutdown')
        await message.channel.send(msg)
        await self.close()

    async def on_no_command(self, *args):
        pass

    def save(self):
        with open('channels.json', 'w') as fout:
            json.dump(self.log_channels, fout)

    async def on_voice_state_update(self, member, before, after):
        gid = str(member.guild.id)
        cid = self.log_channels.get(gid, None)
        if cid is None:
            return

        channel = client.get_channel(cid)
        name = getattr(member, 'nick')
        if name is None:
            name = member.name

        vs = VoiceState(name, before, after)
        msg = vs.get_message()

        if msg is None:
            cs = ChannelState(name, before, after)
            msg = cs.get_message()

        await channel.send(msg)

if __name__ == "__main__":
    client = VoiceLogger()
    client.run(client.config['token'])
