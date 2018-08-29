module.exports = function (RED) {
    "use strict";

    // #41 8-bit port (supplied with 200mm cable)

    var TpCommon = require('./tpCommon');

    function TP_41Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp41", node);

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
    RED.nodes.registerType("Tibbit-#41", TP_41Node);
}

