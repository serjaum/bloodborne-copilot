import struct
import unittest

from tools.bloodborne_save_reader.save_reader import parse_save_bytes


class ParseSaveBytesTests(unittest.TestCase):
    def test_parses_read_only_character_summary(self):
        data = bytearray(80000)
        struct.pack_into("<II", data, 4, 0x16, 3600)
        inventory_offset = 2048
        data[inventory_offset:inventory_offset + 4] = bytes.fromhex("40 f0 ff ff")
        item_offset = inventory_offset + 16
        item_record = bytearray(16)
        item_record[0] = 5
        item_record[4:8] = bytes.fromhex("34 12 00 b0")
        item_record[8:12] = bytes.fromhex("34 12 00 40")
        struct.pack_into("<I", item_record, 12, 7)
        data[item_offset:item_offset + 16] = item_record
        data[inventory_offset + 32:inventory_offset + 48] = bytes.fromhex(
            "01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f 10"
        )  # unclassified record is not reported
        storage_offset = inventory_offset + 34268
        armor_record = bytearray(16)
        armor_record[0] = 9
        armor_record[4:8] = bytes.fromhex("78 56 00 90")
        armor_record[8:12] = bytes.fromhex("78 56 00 10")
        struct.pack_into("<I", armor_record, 12, 1)
        data[storage_offset + 2 * 16:storage_offset + 3 * 16] = armor_record
        aob_offset = 100
        data[aob_offset:aob_offset + 8] = bytes.fromhex("03 00 00 00 05 00 01 00")
        data[aob_offset + 21714] = 0x0F  # community pattern: Cleric Beast defeated bit
        data[aob_offset + 21727] = 0x00  # Father Gascoigne not defeated
        struct.pack_into("<I", data, aob_offset + 360, 64)
        lced_offset = 512
        data[lced_offset:lced_offset + 4] = b"LCED"
        marker = bytes.fromhex("ff ff ff ff 00 00 00 00 00 00 00 00")
        marker_offset = 1024
        data[marker_offset:marker_offset + len(marker)] = marker
        struct.pack_into("<fff", data, marker_offset + 12, -177.5, -23.0, 485.25)
        username_offset = inventory_offset - 469
        data[username_offset + 1:username_offset + 27] = "Hunter Alpha".encode("utf-16le") + b"\0\0"
        for name, distance, value in (
            ("vitality", 103, 25),
            ("endurance", 95, 20),
            ("strength", 79, 18),
            ("skill", 71, 12),
            ("bloodtinge", 63, 7),
            ("arcane", 55, 9),
            ("level", 23, 61),
            ("echoes", 19, 12345),
            ("insight", 35, 8),
        ):
            struct.pack_into("<I", data, username_offset - distance, value)
        struct.pack_into("<III", data, username_offset - 147, 880, 1100, 1100)
        struct.pack_into("<III", data, username_offset - 119, 100, 120, 120)

        summary = parse_save_bytes(bytes(data))

        self.assertEqual(summary["character_name"], "Hunter Alpha")
        self.assertEqual(summary["level"], 61)
        self.assertEqual(summary["stats"]["vitality"], 25)
        self.assertEqual(summary["blood_echoes"], 12345)
        self.assertEqual(summary["insight"], 8)
        self.assertEqual(summary["loaded_map_raw"], 0x16)
        self.assertEqual(summary["playtime_raw"], 3600)
        self.assertEqual(summary["health"], {"current": 880, "max": 1100})
        self.assertEqual(summary["stamina"], {"current": 100, "max": 120})
        self.assertEqual(summary["position_raw"], {"x": -177.5, "y": -23.0, "z": 485.25})
        self.assertTrue(summary["bosses"]["Cleric Beast"])
        self.assertFalse(summary["bosses"]["Father Gascoigne"])
        self.assertEqual(summary["death_count_raw"], 64)
        self.assertEqual(
            summary["inventory"]["carried"],
            [{
                "slot_index": 1,
                "slot_number_raw": 5,
                "kind_candidate": "item",
                "item_id_raw": 0x1234,
                "first_part_raw": 0xB0001234,
                "second_part_raw": 0x40001234,
                "quantity_raw": 7,
                "record_hex": "05 00 00 00 34 12 00 b0 34 12 00 40 07 00 00 00",
            }],
        )
        self.assertEqual(
            summary["inventory"]["storage"],
            [{
                "slot_index": 2,
                "slot_number_raw": 9,
                "kind_candidate": "armor",
                "item_id_raw": 0x5678,
                "first_part_raw": 0x90005678,
                "second_part_raw": 0x10005678,
                "quantity_raw": 1,
                "record_hex": "09 00 00 00 78 56 00 90 78 56 00 10 01 00 00 00",
            }],
        )

    def test_rejects_data_without_bloodborne_inventory_signature(self):
        with self.assertRaisesRegex(ValueError, "Bloodborne inventory signature"):
            parse_save_bytes(bytes(4096))


if __name__ == "__main__":
    unittest.main()
