module.exports = function (RED) {
    "use strict";

    // #53 Isolated 4-20mA ADC

    var TpCommon = require('./tpCommon');

    function TP_53Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common 
        var tc = new TpCommon("tp53", node);

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
    RED.nodes.registerType("Tibbit-#53", TP_53Node);

}
