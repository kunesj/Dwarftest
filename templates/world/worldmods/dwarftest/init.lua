-- Dwarftest definitions required by converted world

WATER_ALPHA = 160
WATER_VISC = 1
LAVA_VISC = 7
LIGHT_MAX = 14

-- Definitions made by this mod that other mods can use too
dwarftest = {}

--
-- Tool definition
--

-- The hand
minetest.register_item(":", {
	type = "none",
	wield_image = "wieldhand.png",
	wield_scale = {x=1, y=1, z=2.5},
	tool_capabilities = {
		full_punch_interval = 1.0,
		max_drop_level = 0,
		groupcaps = {
			crumbly = {times = {0.5, 0.5, 0.5}, uses = 0, maxlevel = 256},
			cracky = {times = {0.5, 0.5, 0.5}, uses = 0, maxlevel = 256},
			snappy = {times = {0.5, 0.5, 0.5}, uses = 0, maxlevel = 256},
			choppy = {times = {0.5, 0.5, 0.5}, uses = 0, maxlevel = 256},
			fleshy = {times = {0.5, 0.5, 0.5}, uses = 0, maxlevel = 256},
			oddly_breakable_by_hand = {times = {0.5, 0.5, 0.5}, uses = 0, maxlevel = 256},
		},
		damage_groups = {fleshy=1},
	}
})

--
-- Sounds
--

function dwarftest.node_sound(table)
	table = table or {}
	table.footstep = table.footstep or {name="", gain=1.0}
	-- table.dug = table.dug or {name="dwarftest_dug_node", gain=1.0}
	return table
end

-- node types

function dwarftest.node_sound_dirt(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_dirt_footstep", gain=0.3}
	dwarftest.node_sound(table)
	return table
end

function dwarftest.node_sound_grass(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_grass_footstep", gain=0.3}
	dwarftest.node_sound(table)
	return table
end

function dwarftest.node_sound_hard(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_hard_footstep", gain=0.3}
	dwarftest.node_sound(table)
	return table
end

function dwarftest.node_sound_metal(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_metal_footstep", gain=0.3}
	dwarftest.node_sound(table)
	return table
end

function dwarftest.node_sound_sand(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_sand_footstep", gain=0.3}
	dwarftest.node_sound(table)
	return table
end

function dwarftest.node_sound_wood(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_wood_footstep", gain=0.3}
	dwarftest.node_sound(table)
	return table
end

-- special node types

function dwarftest.node_sound_leaves(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_grass_footstep", gain=0.45}
	dwarftest.node_sound(table)
	return table
end

function dwarftest.node_sound_water(table)
	table = table or {}
	table.footstep = table.footstep or {name="dwarftest_water_footstep", gain=0.2}
	dwarftest.node_sound(table)
	return table
end

--
-- Static node definitions
--

minetest.register_node("dwarftest:unknown", {
	description = "unknown",
	tiles = {"dwarftest_unknown.png"},
	groups = {
		oddly_breakable_by_hand = 1,
	},
	is_ground_content = false, -- If True, allows cave generation to replace it
	sounds = dwarftest.node_sound_hard(),
})

-- Water

minetest.register_node("dwarftest:water_source", {
	description = "Water Source",
--	drawtype = "liquid",
	drawtype = "glasslike",
	tiles = {
		{
			name = "dwarftest_water_source_animated.png",
			animation = {
				type = "vertical_frames",
				aspect_w = 16,
				aspect_h = 16,
				length = 2.0,
			},
		},
	},
	special_tiles = {
		-- New-style water source material (mostly unused)
		{
			name = "dwarftest_water_source_animated.png",
			animation = {
				type = "vertical_frames",
				aspect_w = 16,
				aspect_h = 16,
				length = 2.0,
			},
			backface_culling = false,
		},
	},
	alpha = 160,
	paramtype = "light",
	walkable = false,
	pointable = false,
	diggable = false,
	buildable_to = true,
	is_ground_content = false,
	drop = "",
	drowning = 1,
--	liquidtype = "source",
--	liquid_alternative_flowing = "dwarftest:water_flowing",
--	liquid_alternative_source = "dwarftest:water_source",
--	liquid_viscosity = 1,
	post_effect_color = {a = 103, r = 30, g = 60, b = 90},
	groups = {water = 3, liquid = 3, puts_out_fire = 1, cools_lava = 1},
	sounds = dwarftest.node_sound_water(),
})

--minetest.register_node("dwarftest:water_flowing", {
--	description = "Flowing Water",
--	drawtype = "flowingliquid",
--	tiles = {"dwarftest_water.png"},
--	special_tiles = {
--		{
--			name = "dwarftest_water_flowing_animated.png",
--			backface_culling = false,
--			animation = {
--				type = "vertical_frames",
--				aspect_w = 16,
--				aspect_h = 16,
--				length = 0.8,
--			},
--		},
--		{
--			name = "dwarftest_water_flowing_animated.png",
--			backface_culling = true,
--			animation = {
--				type = "vertical_frames",
--				aspect_w = 16,
--				aspect_h = 16,
--				length = 0.8,
--			},
--		},
--	},
--	alpha = 160,
--	paramtype = "light",
--	paramtype2 = "flowingliquid",
--	walkable = false,
--	pointable = false,
--	diggable = false,
--	buildable_to = true,
--	is_ground_content = false,
--	drop = "",
--	drowning = 1,
--	liquidtype = "flowing",
--	liquid_alternative_flowing = "dwarftest:water_flowing",
--	liquid_alternative_source = "dwarftest:water_source",
--	liquid_viscosity = 1,
--	post_effect_color = {a = 103, r = 30, g = 60, b = 90},
--	groups = {water = 3, liquid = 3, puts_out_fire = 1,
--		not_in_creative_inventory = 1, cools_lava = 1},
--	sounds = dwarftest.node_sound_water(),
--})

-- Lava

minetest.register_node("dwarftest:lava_source", {
	description = "Lava Source",
--	drawtype = "liquid",
	drawtype = "glasslike",
	tiles = {
		{
			name = "dwarftest_lava_source_animated.png",
			animation = {
				type = "vertical_frames",
				aspect_w = 16,
				aspect_h = 16,
				length = 3.0,
			},
		},
	},
	special_tiles = {
		-- New-style lava source material (mostly unused)
		{
			name = "dwarftest_lava_source_animated.png",
			animation = {
				type = "vertical_frames",
				aspect_w = 16,
				aspect_h = 16,
				length = 3.0,
			},
			backface_culling = false,
		},
	},
	paramtype = "light",
	light_source = LIGHT_MAX - 1,
	walkable = false,
	pointable = false,
	diggable = false,
	buildable_to = true,
	is_ground_content = false,
	drop = "",
	drowning = 1,
--	liquidtype = "source",
--	liquid_alternative_flowing = "dwarftest:lava_flowing",
--	liquid_alternative_source = "dwarftest:lava_source",
--	liquid_viscosity = 7,
--	liquid_renewable = false,
	damage_per_second = 4 * 2,
	post_effect_color = {a = 191, r = 255, g = 64, b = 0},
	groups = {lava = 3, liquid = 2, igniter = 1},
})

--minetest.register_node("dwarftest:lava_flowing", {
--	description = "Flowing Lava",
--	drawtype = "flowingliquid",
--	tiles = {"dwarftest_LAVA.png"},
--	special_tiles = {
--		{
--			name = "dwarftest_lava_flowing_animated.png",
--			backface_culling = false,
--			animation = {
--				type = "vertical_frames",
--				aspect_w = 16,
--				aspect_h = 16,
--				length = 3.3,
--			},
--		},
--		{
--			name = "dwarftest_lava_flowing_animated.png",
--			backface_culling = true,
--			animation = {
--				type = "vertical_frames",
--				aspect_w = 16,
--				aspect_h = 16,
--				length = 3.3,
--			},
--		},
--	},
--	paramtype = "light",
--	paramtype2 = "flowingliquid",
--	light_source = LIGHT_MAX - 1,
--	walkable = false,
--	pointable = false,
--	diggable = false,
--	buildable_to = true,
--	is_ground_content = false,
--	drop = "",
--	drowning = 1,
--	liquidtype = "flowing",
--	liquid_alternative_flowing = "dwarftest:lava_flowing",
--	liquid_alternative_source = "dwarftest:lava_source",
--	liquid_viscosity = 7,
--	liquid_renewable = false,
--	damage_per_second = 4 * 2,
--	post_effect_color = {a = 191, r = 255, g = 64, b = 0},
--	groups = {lava = 3, liquid = 2, igniter = 1,
--		not_in_creative_inventory = 1},
--})

--
-- Dynamic node definitions
--

local function read_file(path)
    local file = io.open(path, "rb") -- r read mode and b binary mode
    if not file then return nil end
    local content = file:read "*a" -- *a or *all reads the whole file
    file:close()
    return content
end

material_list_path = minetest.get_modpath("dwarftest").."/material_list.json"
material_list_json = read_file(material_list_path);
material_list = minetest.parse_json(material_list_json)
--minetest.log("error", minetest.serialize(material_list));

for i = 1, #material_list do
--	minetest.log("error", minetest.serialize(material_list[i]));
	local mat = material_list[i]

	-- get base material texture

	local base_tex
	local mod_tex

	if mat.mt_node == nil or mat.mt_node.material == nil then
		base_tex = "dwarftest_template_empty.png"
	else  -- stone, soil, ice, wood, mushroom, grass, smooth, leaves
		base_tex = string.format("dwarftest_template_%s.png", mat.mt_node.material)
	end

	if mat.mt_node ~= nil and mat.mt_node.shape == "stair" then
		base_tex = ""
		mod_tex = "dwarftest_template_stair.png"
	elseif mat.mt_node ~= nil and mat.mt_node.shape == "fortification" then
		base_tex = ""
		mod_tex = "dwarftest_template_fortification.png"
	else
		mod_tex = ""
	end

	local tex_name = string.format(
		"%s%s^[colorize:#%02x%02x%02x80", base_tex, mod_tex, mat.color[1], mat.color[2], mat.color[3]
	)

	-- get sound

	local sound_fcn

	if mat.mt_node ~= nil and mat.mt_node.material == "soil" then
		sound_fcn = dwarftest.node_sound_dirt
	elseif mat.mt_node ~= nil and mat.mt_node.material == "stone" then
		sound_fcn = dwarftest.node_sound_hard
	elseif mat.mt_node ~= nil and mat.mt_node.material == "ice" then
		sound_fcn = dwarftest.node_sound_hard
	elseif mat.mt_node ~= nil and mat.mt_node.material == "wood" then
		sound_fcn = dwarftest.node_sound_wood
	elseif mat.mt_node ~= nil and mat.mt_node.material == "mushroom" then
		sound_fcn = dwarftest.node_sound_wood
	elseif mat.mt_node ~= nil and mat.mt_node.material == "grass" then
		sound_fcn = dwarftest.node_sound_grass
	elseif mat.mt_node ~= nil and mat.mt_node.material == "smooth" then
		sound_fcn = dwarftest.node_sound_hard
	elseif mat.mt_node ~= nil and mat.mt_node.material == "leaves" then
		sound_fcn = dwarftest.node_sound_leaves
	else
		sound_fcn = dwarftest.node_sound_dirt
	end

	-- create node based on its shape

	if mat.mt_node ~= nil and mat.mt_node.shape == "stair" then

		minetest.register_node(mat.mt_id, {
			description = mat.name,
			drawtype = "glasslike",
			tiles = {tex_name},
			paramtype = "light",
			groups = {
				oddly_breakable_by_hand = 1,
			},
			is_ground_content = false,
			sunlight_propagates = true,
			walkable = false,
			climbable = true,
			post_effect_color = {r=mat.color[1], g=mat.color[2], b=mat.color[3], a=64},
			sounds = sound_fcn(),
		})

	elseif mat.mt_node ~= nil and mat.mt_node.shape == "fortification" then

		minetest.register_node(mat.mt_id, {
			description = mat.name,
			drawtype = "glasslike",
			tiles = {tex_name},
			paramtype = "light",
			groups = {
				oddly_breakable_by_hand = 1,
			},
			is_ground_content = false,
			sunlight_propagates = true,
			sounds = sound_fcn(),
		})

	elseif mat.mt_node ~= nil and mat.mt_node.shape == "leaves" then

		minetest.register_node(mat.mt_id, {
			description = mat.name,
			drawtype = "allfaces_optional",
			visual_scale = 1.3,
			tiles = {tex_name},
			paramtype = "light",
			groups = {
				oddly_breakable_by_hand = 1,
			},
			is_ground_content = false,
			sounds = sound_fcn(),
		})

	else -- normal wall

		minetest.register_node(mat.mt_id, {
			description = mat.name,
			tiles = {tex_name},
			groups = {
				oddly_breakable_by_hand = 1,
			},
			is_ground_content = false,
			sounds = sound_fcn(),
		})

	end

end

---
--- Fix Mapgen errors
---

minetest.register_alias("mapgen_stone", "dwarftest:water_source")
minetest.register_alias("mapgen_water_source", "dwarftest:water_source")
minetest.register_alias("mapgen_river_water_source", "dwarftest:water_source")
