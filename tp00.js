module.exports = function (RED) {
    "use strict";

    // #00 direct I/O lines

    var TpCommon = require('./tpCommon');

    function TP_00Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common 
        var tc = new TpCommon("tp00", node);

        // Launch python
        tc.execPy([config.tpSlot, config.communication, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                if (config.communication != 'Serial') {
                    msg.payload = JSON.parse(payload);
                } else {
                    msg.payload = payload;
                }
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });
    }
    RED.nodes.registerType("Tibbit-#00", TP_00Node);

    function TP_00_InNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp00_in", node);

        // Launch python
        tc.execPy([config.tpSlot, config.communication, config.host]);

        // On Node Output
        tc.onOutput(function (msg, payload) {
            
            try {
                if (config.communication != 'Serial') {
                    msg.payload = JSON.parse(payload);
                } else {
                    msg.payload = Buffer.from(JSON.parse(payload));
                }
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });

    }
    RED.nodes.registerType("Tibbit-#00 in", TP_00_InNode);
}

