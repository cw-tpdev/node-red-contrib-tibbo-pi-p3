/*
 * Raspberry Pi PIC Programmer using GPIO connector
 * https://github.com/WallaceIT/picberry
 * Copyright 2014 Francesco Valla
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

#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <iostream>

#include "pic18f66k40.h"

/* delays (in microseconds) */
#define DELAY_P1   	1
#define DELAY_P2   	1
#define DELAY_P2A  	1
#define DELAY_P2B  	1
#define DELAY_P3   	1
#define DELAY_P4   	1
#define DELAY_P5   	1
#define DELAY_P5A  	1
#define DELAY_P6   	1
#define DELAY_P9  	3400
#define DELAY_P10  	54000
#define DELAY_P11  	524000
#define DELAY_P12  	400
#define DELAY_P13  	1
#define DELAY_P14  	1
#define DELAY_P16  	1
#define DELAY_P17  	3
#define DELAY_P19	4000
#define DELAY_P20	1

#define DELAY_TDLY	(2)

/* commands for programming */
#define COMM_CORE_INSTRUCTION 				0x00
#define COMM_SHIFT_OUT_TABLAT 				0x02
#define COMM_TABLE_READ	     				0x08
#define COMM_TABLE_READ_POST_INC 			0x09
#define COMM_TABLE_READ_POST_DEC			0x0A
#define COMM_TABLE_READ_PRE_INC 			0x0B
#define COMM_TABLE_WRITE					0x0C
#define COMM_TABLE_WRITE_POST_INC_2			0x0D
#define COMM_TABLE_WRITE_STARTP_POST_INC_2	0x0E
#define COMM_TABLE_WRITE_STARTP				0x0F

#define COMM_LOAD_PC_ADDRESS        (0x80)
#define COMM_BULK_ERASE_PG_MEM      (0x18)
#define COMM_LOAD_DATA_NVM          (0x00)
#define COMM_LOAD_DATA_NVM_PC_INC   (0x02)
#define COMM_READ_DATA_NVM          (0xFC)
#define COMM_READ_DATA_NVM_PC_INC   (0xFE)
#define COMM_INC_ADDRESS            (0xF8)
#define COMM_BEGIN_INT_PG           (0xE0)
#define COMM_BEGIN_EXT_PG           (0xC0)
#define COMM_END_EXT_PG             (0x82)

#define ENTER_PROGRAM_KEY	0x4D434850

unsigned int lcounter2 = 0;

void pic18f66k40::enter_program_mode(void)
{
	int i;

	GPIO_IN(pic_mclr);
	GPIO_OUT(pic_mclr);

	GPIO_CLR2(pic_mclr);			/* remove VDD from MCLR pin */
	delay_us(DELAY_P13);	/* wait P13 */
	GPIO_SET2(pic_mclr);			/* apply VDD to MCLR pin */
	delay_us(10);		/* wait (no minimum time requirement) */
	GPIO_CLR2(pic_mclr);			/* remove VDD from MCLR pin */
	delay_us(DELAY_P19);	/* wait P19 */

	GPIO_CLR(pic_clk);
	delay_us(DELAY_P2B);	/* Setup time */
	GPIO_SET(pic_clk);
	delay_us(DELAY_P2A);	/* Hold time */
	GPIO_CLR(pic_clk);
	/* Shift in the "enter program mode" key sequence (MSB first) */
	for (i = 31; i > 0; i--) {
		if ( (ENTER_PROGRAM_KEY >> i) & 0x01 )
			GPIO_SET(pic_data);
		else
			GPIO_CLR(pic_data);
		delay_us(DELAY_P2B);	/* Setup time */
		GPIO_CLR(pic_clk);
		delay_us(DELAY_P2A);	/* Hold time */
		GPIO_SET(pic_clk);

	}
	GPIO_CLR(pic_data);
	delay_us(DELAY_P20);	/* Wait P20 */
	//GPIO_SET2(pic_mclr);			/* apply VDD to MCLR pin */
    GPIO_CLR(pic_clk);
	delay_us(10);
}

void pic18f66k40::exit_program_mode(void)
{

	GPIO_CLR(pic_clk);			/* stop clock on PGC */
	GPIO_CLR(pic_data);			/* clear data pin PGD */
	delay_us(DELAY_P16);	/* wait P16 */
	GPIO_CLR2(pic_mclr);			/* remove VDD from MCLR pin */
	delay_us(DELAY_P17);	/* wait (at least) P17 */
	GPIO_SET2(pic_mclr);
	GPIO_IN(pic_mclr);
}

/* Send a 8-bit command to the PIC (MSB first) */
void pic18f66k40::send_cmd(uint8_t cmd)
{
	int i;

	for (i = 7; i >= 0; i--) {
		GPIO_SET(pic_clk);
		if ( (cmd >> i) & 0x01 )
			GPIO_SET(pic_data);
		else
			GPIO_CLR(pic_data);
		delay_us(DELAY_P2B);	/* Setup time */
		GPIO_CLR(pic_clk);
		delay_us(DELAY_P2A);	/* Hold time */
	}
	GPIO_CLR(pic_data);
}

/* Read 24-bit data from the PIC (MSB first) */
uint32_t pic18f66k40::read_data(void)
{
    int32_t i;
	uint32_t data = 0;

	GPIO_IN(pic_data);

	for (i = 23; i >= 0; i--) {
		GPIO_SET(pic_clk);
		delay_us(1);
		GPIO_CLR(pic_clk);
		if (i != 0) data |= ( GPIO_LEV(pic_data) & 1 ) << (i - 1);
		delay_us(1);
	}
    delay_us(DELAY_TDLY);

	GPIO_IN(pic_data);
	GPIO_OUT(pic_data);
    //cout << hex << data << endl;
	return data & 0xFFFF; // 16bit max
}

/* Load 24-bit data to the PIC (MSB first) */
void pic18f66k40::write_data(uint32_t data)
{
	int32_t i;

	for (i = 23; i >= 0; i--) {
		GPIO_SET(pic_clk);
        if (i != 0) {
		    if ( (data >> (i - 1)) & 1 )
		    	GPIO_SET(pic_data);
		    else
		    	GPIO_CLR(pic_data);
        }
		delay_us(DELAY_P2B);	/* Setup time */
		GPIO_CLR(pic_clk);
		delay_us(DELAY_P2A);	/* Hold time */
	}
	GPIO_CLR(pic_data);
}

/* set Table Pointer */
void pic18f66k40::goto_mem_location(uint32_t data)
{
	send_cmd(COMM_LOAD_PC_ADDRESS);
    delay_us(DELAY_TDLY); 
    write_data(data);
    delay_us(DELAY_TDLY); 
}

/* Read PIC device id word, located at 0x3FFFFE:0x3FFFFF */
bool pic18f66k40::read_device_id(void)
{
	//uint16_t id;
	uint32_t id;
	bool found = 0;

	goto_mem_location(0x3FFFFC);

    send_cmd(COMM_READ_DATA_NVM_PC_INC);
    delay_us(DELAY_TDLY); 
    id = read_data();
    delay_us(DELAY_TDLY); 
	device_rev = id;
    send_cmd(COMM_READ_DATA_NVM_PC_INC);
    delay_us(DELAY_TDLY); 
    id = read_data();
    delay_us(DELAY_TDLY); 

	device_id = id;

	for (unsigned short i=0;i < sizeof(piclist)/sizeof(piclist[0]);i++){

		if (piclist[i].device_id == device_id){

			strcpy(name,piclist[i].name);
			mem.code_memory_size = piclist[i].code_memory_size;
			mem.program_memory_size = 0x0F80018;
			mem.location = (uint16_t*) calloc(mem.program_memory_size,sizeof(uint16_t));
			mem.filled = (bool*) calloc(mem.program_memory_size,sizeof(bool));
			found = 1;
			break;
		}
	}

	return found;
}

/* Blank Check */
uint8_t pic18f66k40::blank_check(void)
{
	uint16_t addr, data;
	uint8_t ret = 0;
#if 0
	if(!flags.debug) cerr << "[ 0%]";
	lcounter2 = 0;

	goto_mem_location(0x000000);

	for(addr = 0; addr < (mem.code_memory_size - 4); addr++){

		send_cmd(COMM_TABLE_READ_POST_INC);
		data = read_data();
		send_cmd(COMM_TABLE_READ_POST_INC);
		data = (read_data() << 8) | (data & 0xFF) ;

		if(data != 0xFFFF) {
			fprintf(stderr, "Chip not Blank! Address: 0x%d, Read: 0x%x.\n",  addr*2, data);
			ret = 1;
			break;
		}

		if(lcounter2 != addr*100/mem.code_memory_size){
			lcounter2 = addr*100/mem.code_memory_size;
			fprintf(stderr, "\b\b\b\b\b[%2d%%]", lcounter2);
		}
	}

	if(!flags.debug) cerr << "\b\b\b\b\b";
#endif
	return ret;

}

/* Bulk erase the chip */
void pic18f66k40::bulk_erase(void)
{
	goto_mem_location(0x300000);
	send_cmd(COMM_BULK_ERASE_PG_MEM);
	delay_us(26 * 1000);
	GPIO_CLR(pic_data);
	delay_us(10 * 1000);
	if(flags.client) fprintf(stdout, "@FIN");
}

/* Read PIC memory and write the contents to a .hex file */
void pic18f66k40::read(char *outfile, uint32_t start, uint32_t count)
{
	uint32_t addr = 0;
	uint16_t data = 0;

	if(!flags.debug) cerr << "[ 0%]";
	if(flags.client) fprintf(stdout, "@000");
	lcounter2 = 0;

	/* Read Memory */

	goto_mem_location(0x000000);

	for (addr = 0; addr < mem.code_memory_size; addr++) {
        send_cmd(COMM_READ_DATA_NVM_PC_INC);
        delay_us(DELAY_TDLY); 
        data = read_data();
        delay_us(DELAY_TDLY); 

		if (flags.debug)
			fprintf(stderr, "  addr = 0x%04X  data = 0x%04X\n", addr*2, data);

		if (data != 0xFFFF) {
			mem.location[addr]        = data;
			mem.filled[addr]      = 1;
		}

		if(lcounter2 != addr*100/mem.code_memory_size){
			if(flags.client)
				fprintf(stderr,"RED@%2d\n", (addr*100/mem.code_memory_size));
			if(!flags.debug)
				fprintf(stderr,"\b\b\b\b%2d%%]", addr*100/mem.code_memory_size);
			lcounter2 = addr*100/mem.code_memory_size;
		}
	}

    // User ID
    uint32_t base = 0x200000;
	goto_mem_location(base);
	for (addr = 0; addr < 8; addr++) {
        send_cmd(COMM_READ_DATA_NVM_PC_INC);
        delay_us(DELAY_TDLY); 
        data = read_data();
        delay_us(DELAY_TDLY); 
		if (data != 0xFFFF) {
			mem.location[base/2 + addr] = data;
			mem.filled[base/2 + addr]   = 1;
		}
    }

    // Configuration Words
    base = 0x300000;
	goto_mem_location(base);
	for (addr = 0; addr < 6; addr++) {
        send_cmd(COMM_READ_DATA_NVM_PC_INC);
        delay_us(DELAY_TDLY); 
        data = read_data();
        delay_us(DELAY_TDLY); 
		if (data != 0xFFFF) {
			mem.location[base/2 + addr] = data;
			mem.filled[base/2 + addr]   = 1;
		}
    }

	if(!flags.debug) cerr << "\b\b\b\b\b";
	if(flags.client) fprintf(stdout, "@FIN");
	write_inhx(&mem, outfile);
}

/* Bulk erase the chip, and then write contents of the .hex file to the PIC */
void pic18f66k40::write(char *infile)
{
	int i;
	uint16_t data;
	uint32_t addr = 0x00000000;
	unsigned int filled_locations=1;

	filled_locations = read_inhx(infile, &mem);

	bulk_erase();


	if(!flags.debug) cerr << "[ 0%]";
	if(flags.client) fprintf(stdout, "@000");
	lcounter2 = 0;
    
    // Write Program Memory
	for (addr = 0; addr < mem.code_memory_size; addr += 32){ 
		goto_mem_location(2*addr);
		if (flags.debug)
			fprintf(stderr, "Go to address 0x%08X \n", addr);
		for (i = 0; i < 32; i++){
			if (mem.filled[addr+i]) {
				if (flags.debug)
					fprintf(stderr, "  Writing 0x%04X to address 0x%06X \n", mem.location[addr + i], (addr+i)*2 );
                send_cmd(COMM_LOAD_DATA_NVM_PC_INC);
                delay_us(DELAY_TDLY); 
                write_data(mem.location[addr+i]);
                delay_us(DELAY_TDLY); 
			}
			else {
				if (flags.debug)
					fprintf(stderr, "  Writing 0xFFFF to address 0x%06X \n", (addr+i)*2 );
                send_cmd(COMM_LOAD_DATA_NVM_PC_INC);
                delay_us(DELAY_TDLY); 
			    write_data(0xFFFF);	/* write 0xFFFF in empty locations */
                delay_us(DELAY_TDLY); 
            }
        }

		/* Programming Sequence */
		goto_mem_location(2*addr);
        send_cmd(COMM_BEGIN_EXT_PG);
        delay_us(2500); 
        send_cmd(COMM_END_EXT_PG);
        delay_us(400); 
		/* end of Programming Sequence */

		if(lcounter2 != addr*100/mem.code_memory_size){
			lcounter2 = addr*100/mem.code_memory_size;
			if(flags.client)
				fprintf(stdout,"@%03d", lcounter2);
			if(!flags.debug)
				fprintf(stderr,"\b\b\b\b\b[%2d%%]", lcounter2);
		}
    }
	if(!flags.debug) cerr << "\b\b\b\b\b\b";
	if(flags.client) fprintf(stdout, "@100");

    // Verify Program Memory
	if(!flags.noverify){
		if(!flags.debug) cerr << "[ 0%]";
		if(flags.client) fprintf(stdout, "@000");
		lcounter2 = 0;

	    goto_mem_location(0x000000);
	    for (addr = 0; addr < mem.code_memory_size; addr++) {
            send_cmd(COMM_READ_DATA_NVM_PC_INC);
            delay_us(DELAY_TDLY); 
	    	data = read_data();
            delay_us(DELAY_TDLY); 
	    	if (flags.debug)
	    		fprintf(stderr, "addr = 0x%06X:  pic = 0x%04X, file = 0x%04X\n",
	    			addr*2, data, (mem.filled[addr]) ? (mem.location[addr]) : 0xFFFF);
	    	if ( (data != mem.location[addr]) & (mem.filled[addr]) ) {
	    		fprintf(stderr, "Error at addr = 0x%06X:  pic = 0x%04X, file = 0x%04X.\nExiting...",
	    				addr*2, data, mem.location[addr]);
	    		break;
	    	}
			if(lcounter2 != addr*100/mem.code_memory_size){
				lcounter2 = addr*100/mem.code_memory_size;
				if(flags.client)
					fprintf(stdout,"@%03d", lcounter2);
				if(!flags.debug)
					fprintf(stderr,"\b\b\b\b\b[%2d%%]", lcounter2);
			}
        }
		if(!flags.debug) cerr << "\b\b\b\b\b";
		if(flags.client) fprintf(stdout, "@FIN");
	}
	else{
		if(flags.client) fprintf(stdout, "@FIN");
	}

    // Write User ID
    write_ex_data(0x200000, 8);

    // Verify User ID
	if(!flags.noverify) verify_data(0x200000, 8);
    
    // Write Configuration Words
    write_ex_data(0x300000, 6);

    // Verify Configuration Words
	if(!flags.noverify) verify_data(0x300000, 6);

}

/* Dum configuration words */
void pic18f66k40::dump_configuration_registers(void)
{

	cout << "Configuration Words:" << endl;

    // User ID
	goto_mem_location(0x200000);
	for (int i = 0; i < 8; i++) {
        send_cmd(COMM_READ_DATA_NVM_PC_INC);
        delay_us(DELAY_TDLY); 
		fprintf(stdout, " - User ID%d = 0x%04x\n", i, read_data());
        delay_us(DELAY_TDLY); 
    }

    // Configuration Word
	goto_mem_location(0x300000);
	for (int i = 1; i <= 6; i++) {
        send_cmd(COMM_READ_DATA_NVM_PC_INC);
        delay_us(DELAY_TDLY); 
		fprintf(stdout, " - CONFIG%d = 0x%04x\n", i, read_data());
        delay_us(DELAY_TDLY); 
    }

	cout << endl;
}

void pic18f66k40::write_ex_data(uint32_t base_addr, uint32_t num)
{
    uint32_t addr = 0;

	for (addr = 0; addr < num; addr++) {
	    goto_mem_location(base_addr + addr*2);
		if (mem.filled[base_addr/2 + addr]) {
			if (flags.debug)
				fprintf(stderr, "  Writing 0x%04X to address 0x%06X \n", mem.location[base_addr/2 + addr], base_addr + addr*2 );
            send_cmd(COMM_LOAD_DATA_NVM);
            delay_us(DELAY_TDLY); 
            write_data(mem.location[base_addr/2 + addr]);
            delay_us(DELAY_TDLY); 
		} else {
			if (flags.debug)
				fprintf(stderr, "  Writing 0xFFFF to address 0x%06X \n", base_addr + addr*2 );
            send_cmd(COMM_LOAD_DATA_NVM);
            delay_us(DELAY_TDLY); 
            write_data(0xFFFF);
            delay_us(DELAY_TDLY); 
        }
		/* Programming Sequence */
        send_cmd(COMM_BEGIN_INT_PG);
        delay_us(3000); 
    }
}

void pic18f66k40::verify_data(uint32_t base_addr, uint32_t num)
{
    uint32_t addr = 0;
    uint16_t data = 0;

    goto_mem_location(base_addr);

	for (addr = 0; addr < num; addr++) {
        send_cmd(COMM_READ_DATA_NVM_PC_INC);
        delay_us(DELAY_TDLY); 
	    data = read_data();
        delay_us(DELAY_TDLY); 
	    if (flags.debug)
	    	fprintf(stderr, "addr = 0x%06X:  pic = 0x%04X, file = 0x%04X\n",
	    		base_addr + addr*2, data, (mem.filled[base_addr/2 + addr]) ? (mem.location[base_addr/2 + addr]) : 0xFFFF);
	    if ( (data != mem.location[base_addr/2 + addr]) & (mem.filled[base_addr/2 + addr]) ) {
            if (base_addr + addr*2 != 0x300006) fprintf(stderr, "Error at addr = 0x%06X:  pic = 0x%04X, file = 0x%04X.\nExiting...", base_addr + addr*2, data, mem.location[base_addr/2 + addr]);
	    	break;
	    }

    }
}
