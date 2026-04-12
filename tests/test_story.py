from src.story import DialogueNode, DialogueOption, StoryManager


def test_story_alignment_updates_on_choice() -> None:
    manager = StoryManager()
    manager.register_dialogue(
        DialogueNode(
            id="start",
            speaker="Narrator",
            text="Choose",
            options=[DialogueOption(text="Law", leads_to="end", alignment_impact=25)],
        )
    )
    manager.register_dialogue(DialogueNode(id="end", speaker="Narrator", text="Done"))

    manager.start_dialogue("start")
    next_node = manager.advance_dialogue(0)

    assert manager.player_alignment == 25
    assert next_node is not None
    assert next_node.id == "end"
