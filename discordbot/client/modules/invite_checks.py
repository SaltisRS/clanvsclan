import discord
import os
from dotenv import load_dotenv




class InviteTracker:
    load_dotenv()
    IF_INVITE = os.getenv("IF_INVITE")
    IC_INVITE = os.getenv("IC_INVITE")
    IF_ROLE = os.getenv("IF_ROLE")
    IC_ROLE = os.getenv("IC_ROLE")
    def __init__(self, client: discord.Client, guild: discord.Guild):
        self.client = client
        self.guild = guild
        self.invite_cache = {}
        self.invite_roles = {
            "if": {"role": self.guild.get_role(int(self.IF_ROLE) if self.IF_ROLE else 0),
                   "code": self.IF_INVITE},
            "ic": {"role": self.guild.get_role(int(self.IC_ROLE if self.IC_ROLE else 0)),
                   "code": self.IC_INVITE}
        }
    
    async def startup_cache(self):
        for invite in await self.guild.invites():
            self.invite_cache[invite.code] = invite.uses
            
    async def add_role(self, member: discord.Member, invite: discord.Invite):
        for _, v in self.invite_roles.items():
            if invite.code == v["code"]:
                await member.add_roles(*[v["role"]]) # type: ignore
                return
            
    async def new_member(self, member: discord.Member):
        for invite in await self.guild.invites():
            if invite.code not in self.invite_cache:
                continue
            if invite.uses > self.invite_cache[invite.code]:
                self.invite_cache[invite.code] = invite.uses
                await self.add_role(member, invite)
                break
    
    
    