import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zei_userbot.runtime import Runtime, HELP
from zei_userbot.state import State
from zei_userbot.tools import calculate, execute


class ToolsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=State(Path(self.tmp.name)/"account.sqlite")
        self.client=SimpleNamespace(edit_permissions=AsyncMock(),kick_participant=AsyncMock(),edit_admin=AsyncMock(),delete_messages=AsyncMock(),get_entity=AsyncMock(return_value=SimpleNamespace(id=3)))
        self.runtime=SimpleNamespace(owner=2,state=self.state,client=self.client)
        self.event=SimpleNamespace(client=self.client,chat_id=-100123,is_private=False,get_reply_message=AsyncMock(return_value=SimpleNamespace(get_sender=AsyncMock(return_value=SimpleNamespace(id=3)))))

    async def asyncTearDown(self):
        self.state.close();self.tmp.cleanup()

    def test_calculator_rejects_execution_and_resource_abuse(self):
        self.assertEqual(calculate("2*(3+4)-1"),13)
        for text in ("__import__('os')", "2**999999", "[1]*999", "10**1000000", "1e300", "a", "1/0", "1"*121):
            with self.assertRaises((ValueError,ZeroDivisionError,SyntaxError)): calculate(text)

    async def test_ban_unban_and_no_owner_target(self):
        await execute(self.runtime,"ban","user",self.event)
        self.client.edit_permissions.assert_awaited_with(-100123,self.client.get_entity.return_value,view_messages=False)
        await execute(self.runtime,"unban","user",self.event)
        self.client.edit_permissions.assert_awaited_with(-100123,self.client.get_entity.return_value,view_messages=True)
        self.client.get_entity.return_value=SimpleNamespace(id=2)
        self.client.edit_permissions.reset_mock()
        await execute(self.runtime,"ban","self",self.event)
        self.client.edit_permissions.assert_not_awaited()

    async def test_filters_validate_and_persist_per_account(self):
        await execute(self.runtime,"filter","halo | Hai teman",self.event)
        self.assertEqual(self.state.get("filters"),{"halo":"Hai teman"})
        await execute(self.runtime,"delfilter","halo",self.event)
        self.assertEqual(self.state.get("filters"),{})

    async def test_pmpermit_grants_specific_sender(self):
        await execute(self.runtime,"pmpermit","on",self.event)
        await execute(self.runtime,"approve","user",self.event)
        self.assertEqual(self.state.get("approved"),[3])
        await execute(self.runtime,"disapprove","user",self.event)
        self.assertEqual(self.state.get("approved"),[])

    def test_commands_have_help_and_owner_filter(self):
        runtime=object.__new__(Runtime);runtime.owner=2;runtime.state=self.state
        for command in HELP:
            self.assertIsNotNone(runtime.parse("."+command,2))
            self.assertIsNone(runtime.parse("."+command,3))
            self.assertIsNone(runtime.parse("."+command,2,False))
