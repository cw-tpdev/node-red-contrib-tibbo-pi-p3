/*
 * Raspberry Pi PIC Programmer using GPIO connector
 * https://github.com/WallaceIT/picberry
 * Copyright 2016 Francesco Valla
 *
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
 
#ifndef DEVICE_H_
#define DEVICE_H_
 
 struct memory{
		uint32_t	program_memory_size;   	// size in WORDS (16bits each)
		uint32_t	code_memory_size;		// size in WORDS (16bits each)
		uint16_t	*location;		// 16-bit data
		bool		*filled;		// 1 if the corresponding location is used
};

struct pic_device{
	uint32_t    device_id;
	char        name[25];
	int			code_memory_size;	/* size in WORDS (16bits each)  */
};

class Pic{

	public:
		uint32_t 		device_id;
		uint16_t 		device_rev;
		uint8_t			subfamily;
		char			name[25];
		memory 			mem;

		Pic(uint8_t sf=0){
			device_id=0;
			device_rev=0;
			subfamily=sf;
		};
		virtual ~Pic(){};

		virtual void enter_program_mode(void) = 0;
		virtual void exit_program_mode(void) = 0;
		virtual bool setup_pe(void) = 0;
		virtual bool read_device_id(void) = 0;
		virtual void bulk_erase(void) = 0;
		virtual void dump_configuration_registers(void) = 0;
		virtual void read(char *outfile, uint32_t start=0, uint32_t count=0) = 0;
		virtual void write(char *infile) = 0;
		virtual uint8_t blank_check(void) = 0;
};

#endif