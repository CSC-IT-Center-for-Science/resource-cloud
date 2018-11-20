app.controller('InitializationController', ['$scope', '$location', 'Restangular', function($scope, $location, Restangular) {
    var initialize = Restangular.all('initialize');
    var initialized = false;

    $scope.initialize_user = function() {
        var params = { eppn: $scope.user.eppn,
                       email_id: $scope.user.eppn,
                       password: $scope.user.password};
        initialize.post(params).then(function(response) {
            $.notify({message: 'You have successfully created admin account: ' + response.eppn + '. Please login with this email and password'}, {type: 'success'});
	    $location.path("/");
        }, function() {
            initialized = true;
        });
    };

    $scope.isInitialized = function() {
        return initialized;
    };
}]);
