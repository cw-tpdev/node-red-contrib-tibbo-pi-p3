module.exports = function (RED) {
    "use strict";

    // #40 Digital potentiometer

    var TpCommon = require('./tpCommon');

    function TP_40_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp40_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("Tibbit-#40 out", TP_40_OutNode);
}
