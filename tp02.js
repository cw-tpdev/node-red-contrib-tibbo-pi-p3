module.exports = function (RED) {
    "use strict";

    // #02 RS232/422/485 port

    var TpCommon = require('./tpCommon');

    function TP_02Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp02", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                msg.payload = JSON.parse(payload);
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });

    }
    RED.nodes.registerType("Tibbit-#02", TP_02Node);

    function TP_02_InNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp02_in", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                var node_data = JSON.parse(payload);
                if (Array.isArray(node_data)) {
                    // buffer
                    msg.payload = Buffer.from(node_data);
                    node.send([msg, null]);
                } else {
                    // gpio
                    msg.payload = node_data;
                    node.send([null, msg]);
                }
            } catch (e) {
                msg.payload = null;
                node.send([msg, null]);
            }
        });
    }
    RED.nodes.registerType("Tibbit-#02 in", TP_02_InNode);
}

