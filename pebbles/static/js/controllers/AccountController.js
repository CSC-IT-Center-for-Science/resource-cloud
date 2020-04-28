app.controller('AccountController', ['$q', '$scope', '$timeout', 'AuthService', 'Restangular', '$uibModal',
                             function($q,   $scope,   $timeout,   AuthService,   Restangular,   $uibModal) {
    var user = Restangular.one('users', AuthService.getUserId());
    var quota = Restangular.one('quota', AuthService.getUserId());
    var workspace_join = Restangular.all('workspaces').one('workspace_join');

    var change_password_result = "";
    var upload_ok = null;

    $scope.getUserName = AuthService.getUserName;

    $scope.isAdmin = function() {
        return AuthService.isAdmin();
    };

    $scope.isWorkspaceManagerOrAdmin = function() {
        return AuthService.isWorkspaceManagerOrAdmin();
    };

    quota.get().then(function (response) {
                $scope.credits_spent = response.credits_spent;
                $scope.credits_quota = response.credits_quota;
            });

    var workspace_list_exit = Restangular.all('workspaces').all('workspace_list_exit');
    var refresh_workspace_list_exit = function(){
        workspace_list_exit.getList().then(function (response) {
            $scope.workspace_list_exit = response;
        });
    };

    refresh_workspace_list_exit();

    $scope.exit_workspace = function(workspace) {
        var workspace_exit = Restangular.all('workspaces').one('workspace_exit').one(workspace.id);
        workspace_exit.put().then(function () {
               refresh_workspace_list_exit();
            }, function(response) {
                $.notify({title: 'HTTP ' + response.status, message: response.data.error}, {type: 'danger'});
            });

     };

    $scope.change_password_msg_visible = function() {
        if (change_password_result === "") {
            return false;
        }
        return true;
    };

    $scope.change_password_msg = function() {
        return change_password_result;
    };

    $scope.update_password = function() {
        user.password = $scope.user.password;
        user.put().then(function() {
            change_password_result = "Password changed";
        }, function(response) {
            var deferred = $q.defer();
            if (response.status === 422) {
                change_password_result = response.data.password.join(', ');
                return deferred.reject(false);
            } else {
                throw new Error("No handler for status code " + response.status);
            }
        });
        $timeout(function() {
            change_password_result = "";
        }, 10000);
    };

    $scope.openWorkspaceJoinModal=function() {
         $uibModal.open({
         templateUrl: '/partials/modal_workspace_join.html',
         controller: 'ModalWorkspaceJoinController',
         size: 'sm',
         resolve: {
             workspace_join: function() {
                 return workspace_join;
             },
             join_title: function() {
                 return "Join A Workspace";
             },
             dismiss_reason: function(){
                 return "You did not join a workspace";
             }
         }
         }).result.then(function() {
                 refresh_workspace_list_exit();
             });
     };
}]);

app.controller('ModalWorkspaceJoinController', function($scope, $modalInstance, workspace_join, join_title, dismiss_reason) {
    $scope.join_title = join_title;
    var grp_join_sf = {};
    grp_join_sf.schema = {
            "type": "object",
            "title": "Comment",
            "properties": {
            "join_code":  {
                "title": "Joining Code",
                "type": "string",
                "description": "The code/password to join your workspace"
                }
            },
            "required": ["join_code"]

    };
    grp_join_sf.form = [
            {"key": "join_code", "type": "textfield", "placeholder": "paste the joining code here"}
    ];
    grp_join_sf.model = {};
    $scope.grp_join_sf = grp_join_sf;
    $scope.workspace_join = workspace_join;

    $scope.joinWorkspace = function(form, model) {
        if (form.$valid) {
            $scope.workspace_join.one(model.join_code).customPUT().then(function () {
                $.notify({title: 'Success! ', message: 'Workspace Joined'}, {type: 'success'});
                $modalInstance.close(true);
            }, function(response) {
                $.notify({title: 'HTTP ' + response.status, message: response.data.error}, {type: 'danger'});
            });
        }
    };

    $scope.cancel = function() {
        if(dismiss_reason){
            $.notify({title: 'GROUP JOINING CANCELLED ! :', message: dismiss_reason}, {type: 'danger'});
        }
        $modalInstance.dismiss('cancel');
    };
});
